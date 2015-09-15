from datetime import datetime, timedelta
from gettext import gettext as _
import itertools
import logging
import platform
import threading
import time

from celery import beat
import mongoengine

from pulp.common.constants import (CELERYBEAT_WAIT_SECONDS, RESOURCE_MANAGER_WORKER_NAME,
                                   SCHEDULER_WORKER_NAME, TICK_SECONDS)
from pulp.server.async import worker_watcher
from pulp.server.async.celery_instance import celery as app
from pulp.server.async.tasks import _delete_worker
from pulp.server.db import connection as db_connection
from pulp.server.db.connection import UnsafeRetry
from pulp.server.db.model.dispatch import ScheduledCall, ScheduleEntry
from pulp.server.db.model import Worker, CeleryBeatLock
from pulp.server.managers.schedule import utils

# The import below is not used in this module, but it needs to be kept here. This module is the
# first and only Pulp module to be imported by celerybeat, and by importing pulp.server.logs, it
# configures the celerybeat logging to log as Pulp does.
import pulp.server.logs  # noqa


_logger = logging.getLogger(__name__)


class EventMonitor(threading.Thread):
    """
    The EventMonitor is a thread dedicated to handling worker discovery/departure.
    """

    def __init__(self):
        super(EventMonitor, self).__init__()

    def run(self):
        """
        The thread entry point, which calls monitor_events().

        monitor_events() is a blocking call, but in the case where an unexpected Exception is
        raised, a log-but-continue behavior is desired. This is especially the case given this is
        a background thread. Exiting is not a concern because this is a daemon=True thread. The
        method loops unconditionally using a try/except pattern around the call to
        monitor_events() to log and then re-enter if an exception is encountered.
        """
        while True:
            try:
                self.monitor_events()
            except Exception as e:
                _logger.error(e)
            time.sleep(10)

    def monitor_events(self):
        """
        Process Celery events.

        Receives events from Celery and matches each with the appropriate handler function. The
        following events are monitored for: 'task-failed', 'task-succeeded', 'worker-heartbeat',
        and 'worker-offline'. The call to capture() is blocking, and does not return.

        Capture is called with wakeup=True causing a gratuitous 'worker-heartbeat' to be sent
        from all workers. This should handle the case of worker discovery where workers already
        exist, and this EventMonitor is started afterwards.

        The call to capture is wrapped in a log-but-continue try/except statement, which along
        with the loop will cause the capture method to be re-entered.
        """
        with app.connection() as connection:
            recv = app.events.Receiver(connection, handlers={
                'worker-heartbeat': worker_watcher.handle_worker_heartbeat,
                'worker-offline': worker_watcher.handle_worker_offline,
                'worker-online': worker_watcher.handle_worker_heartbeat,
            })
            _logger.info(_('Event Monitor Starting'))
            recv.capture(limit=None, timeout=None, wakeup=True)


class CeleryProcessTimeoutMonitor(threading.Thread):
    """
    A thread dedicated to monitoring Celery processes that have stopped checking in.

    Once a Celery process is determined to be missing it logs and handles cleanup appropriately.
    """

    # The amount of time in seconds before a Celery process is considered missing
    CELERY_TIMEOUT_SECONDS = 300

    # The frequency in seconds with which this thread should look for missing Celery processes.
    FREQUENCY = 60

    def run(self):
        """
        The thread entry point. Sleep for FREQUENCY seconds, then call check_celery_processes()

        This method has a try/except block around check_celery_processes() to add durability to
        this background thread.
        """
        _logger.info(_('Worker Timeout Monitor Started'))
        while True:
            time.sleep(self.FREQUENCY)
            try:
                self.check_celery_processes()
            except Exception as e:
                _logger.error(e)

    def check_celery_processes(self):
        """
        Look for missing Celery processes, log and cleanup as needed.

        To find a missing Celery process, filter the Workers model for entries older than
        utcnow() - WORKER_TIMEOUT_SECONDS. The heartbeat times are stored in native UTC, so this is
        a comparable datetime. For each missing worker found, call _delete_worker() synchronously
        for cleanup.

        This method also checks that at least one resource_manager and one scheduler process is
        present. If there are zero of either, log at the error level that Pulp will not operate
        correctly.
        """
        msg = _('Checking if pulp_workers, pulp_celerybeat, or pulp_resource_manager '
                'processes are missing for more than %d seconds') % self.CELERY_TIMEOUT_SECONDS
        _logger.debug(msg)
        oldest_heartbeat_time = datetime.utcnow() - timedelta(seconds=self.CELERY_TIMEOUT_SECONDS)
        worker_list = Worker.objects.all()
        worker_count = 0
        resource_manager_count = 0
        scheduler_count = 0
        for worker in worker_list:
            if worker.last_heartbeat < oldest_heartbeat_time:
                msg = _("Worker '%s' has gone missing, removing from list of workers") % worker.name
                _logger.error(msg)
                _delete_worker(worker.name)
            elif worker.name.startswith(SCHEDULER_WORKER_NAME):
                scheduler_count = scheduler_count + 1
            elif worker.name.startswith(RESOURCE_MANAGER_WORKER_NAME):
                resource_manager_count = resource_manager_count + 1
            else:
                worker_count = worker_count + 1
        if resource_manager_count == 0:
            msg = _("There are 0 pulp_resource_manager processes running. Pulp will not operate "
                    "correctly without at least one pulp_resource_mananger process running.")
            _logger.error(msg)
        if scheduler_count == 0:
            msg = _("There are 0 pulp_celerybeat processes running. Pulp will not operate "
                    "correctly without at least one pulp_celerybeat process running.")
            _logger.error(msg)
        output_dict = {'workers': worker_count, 'celerybeat': scheduler_count,
                       'resource_manager': resource_manager_count}
        msg = _("%(workers)d pulp_worker processes, %(celerybeat)d "
                "pulp_celerybeat processes, and %(resource_manager)d "
                "pulp_resource_manager processes") % output_dict
        _logger.debug(msg)


class Scheduler(beat.Scheduler):
    """
    This is a custom Scheduler object to be used by celery beat.

    This object has two purposes: Implement a dynamic periodic task schedule, and start helper
    threads related to celery event monitoring.

    Celery uses lazy instantiation, so this object may be created multiple times, with some objects
    being thrown away after being created. The spawning of threads needs to be done on the actual
    object, and not any intermediate objects, so __init__ conditionally spawns threads based on
    this case. Threads are spawned using spawn_pulp_monitor_threads().

    Two threads are started, one that uses EventMonitor, and handles all Celery events. The
    second, is a WorkerTimeoutMonitor thread that watches for cases where all workers disappear
    at once.
    """
    Entry = ScheduleEntry

    # the superclass reads this attribute, which is the maximum number of seconds
    # that will ever elapse before the scheduler looks for new or changed schedules.
    max_interval = 90

    # allows mongo initialization to occur exactly once during the first call to setup_schedule()
    _mongo_initialized = False

    def __init__(self, *args, **kwargs):
        """
        Initialize the Scheduler object.

        __init__ may be called multiple times because of the lazy instantiation behavior of Celery.
        If a keyword argument named 'lazy' is set to False, this instantiation is the 'real' one,
        and should create the necessary pulp helper threads using spawn_pulp_monitor_threads().
        """
        self._schedule = None
        self._loaded_from_db_count = 0

        # Force the use of the Pulp celery_instance when this custom Scheduler is used.
        kwargs['app'] = app

        # Leave helper threads starting here if lazy=False due to Celery lazy instantiation
        # https://github.com/celery/celery/issues/1549
        if kwargs.get('lazy', True) is False:
            self.spawn_pulp_monitor_threads()
        super(Scheduler, self).__init__(*args, **kwargs)

    def spawn_pulp_monitor_threads(self):
        """
        Start two threads that are important to Pulp. One monitors workers, the other, events.

        Two threads are started, one that uses EventMonitor, and handles all Celery events. The
        second, is a WorkerTimeoutMonitor thread that watches for cases where all workers
        disappear at once.

        Both threads are set with daemon = True so that if the main thread exits, both will
        close automatically. After being daemonized they are each started with a call to start().

        This method should be called only in certain situations, see docstrings on the object for
        more details.
        """
        # start monitoring events in a thread
        event_monitor = EventMonitor()
        event_monitor.daemon = True
        event_monitor.start()
        # start monitoring workers who may timeout
        worker_timeout_monitor = CeleryProcessTimeoutMonitor()
        worker_timeout_monitor.daemon = True
        worker_timeout_monitor.start()

    @staticmethod
    def call_tick(self, celerybeat_name):
        ret = super(Scheduler, self).tick()
        _logger.debug(_("%(celerybeat_name)s will tick again in %(ret)s secs")
                      % {'ret': ret, 'celerybeat_name': celerybeat_name})
        return ret

    def tick(self):
        """
        Superclass runs a tick, that is one iteration of the scheduler. Executes all due tasks.

        This method updates the last heartbeat time of the scheduler. We do not actually send a
        heartbeat message since it would just get read again by this class.

        :return:    number of seconds before the next tick should run
        :rtype:     float
        """
        # Setting the celerybeat name
        celerybeat_name = SCHEDULER_WORKER_NAME + "@" + platform.node()

        # this is not an event that gets sent anywhere. We process it
        # immediately.
        scheduler_event = {'timestamp': time.time(),
                           'type': 'scheduler-event',
                           'hostname': celerybeat_name}
        worker_watcher.handle_worker_heartbeat(scheduler_event)

        old_timestamp = datetime.utcnow() - timedelta(seconds=CELERYBEAT_WAIT_SECONDS)

        # Updating the current lock if lock is on this instance of celerybeat
        result = CeleryBeatLock.objects(celerybeat_name=celerybeat_name).\
            update(set__timestamp=datetime.utcnow())

        # If current instance has lock and updated lock_timestamp, call super
        if result == 1:
            _logger.debug(_('Lock updated by %(celerybeat_name)s')
                          % {'celerybeat_name': celerybeat_name})
            ret = self.call_tick(self, celerybeat_name)
        else:
            # check for old enough time_stamp and remove if such lock is present
            CeleryBeatLock.objects(timestamp__lte=old_timestamp).delete()
            try:
                lock_timestamp = datetime.utcnow()

                # Insert new lock entry
                new_lock = CeleryBeatLock(celerybeat_name=celerybeat_name,
                                          timestamp=lock_timestamp)
                new_lock.save()
                _logger.info(_("New lock acquired by %(celerybeat_name)s") %
                             {'celerybeat_name': celerybeat_name})
                # After acquiring new lock call super to dispatch tasks
                ret = self.call_tick(self, celerybeat_name)

            except mongoengine.NotUniqueError:
                # Setting a default wait time for celerybeat instances with no lock
                ret = TICK_SECONDS
                _logger.info(_("Duplicate or new celerybeat Instance, "
                               "ticking again in %(ret)s seconds.")
                             % {'ret': ret})
        return ret

    def setup_schedule(self):
        """
        This loads enabled schedules from the database and adds them to the
        "_schedule" dictionary as instances of celery.beat.ScheduleEntry
        """
        if not Scheduler._mongo_initialized:
            _logger.debug('Initializing Mongo client connection to read celerybeat schedule')
            db_connection.initialize()
            Scheduler._mongo_initialized = True
        _logger.debug(_('loading schedules from app'))
        self._schedule = {}
        for key, value in self.app.conf.CELERYBEAT_SCHEDULE.iteritems():
            self._schedule[key] = beat.ScheduleEntry(**dict(value, name=key))

        # include a "0" as the default in case there are no schedules to load
        update_timestamps = [0]

        _logger.debug(_('loading schedules from DB'))
        ignored_db_count = 0
        self._loaded_from_db_count = 0
        for call in itertools.imap(ScheduledCall.from_db, utils.get_enabled()):
            if call.remaining_runs == 0:
                _logger.debug(
                    _('ignoring schedule with 0 remaining runs: %(id)s') % {'id': call.id})
                ignored_db_count += 1
            else:
                self._schedule[call.id] = call.as_schedule_entry()
                update_timestamps.append(call.last_updated)
                self._loaded_from_db_count += 1

        _logger.debug('loaded %(count)d schedules' % {'count': self._loaded_from_db_count})

        self._most_recent_timestamp = max(update_timestamps)

    @property
    @UnsafeRetry.retry_decorator()
    def schedule_changed(self):
        """
        Looks at the update timestamps in the database to determine if there
        are new or modified schedules.

        Indexing should make this very fast.

        :return:    True iff the set of enabled scheduled calls has changed
                    in the database.
        :rtype:     bool
        """
        if utils.get_enabled().count() != self._loaded_from_db_count:
            logging.debug(_('number of enabled schedules has changed'))
            return True

        if utils.get_updated_since(self._most_recent_timestamp).count() > 0:
            logging.debug(_('one or more enabled schedules has been updated'))
            return True

        return False

    @property
    def schedule(self):
        """
        :return:    dictionary where keys are schedule ids and values are
                    instances of celery.beat.ScheduleEntry. These instances are
                    the schedules currently in active use by the scheduler.
        :rtype:     dict
        """
        if self._schedule is None:
            return self.get_schedule()

        if self.schedule_changed:
            self.setup_schedule()

        return self._schedule

    def add(self, **kwargs):
        """
        This class does not support adding entries in-place. You must add new
        entries to the database, and they will be picked up automatically.
        """
        raise NotImplementedError
