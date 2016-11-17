import logging
import platform
import threading
import time
from datetime import datetime, timedelta
from gettext import gettext as _

from celery import beat
from django.utils import timezone
from django.db import IntegrityError

from pulp.app.models.task import TaskLock, Worker
from pulp.tasking import worker_watcher
from pulp.tasking.celery_instance import celery as app
from pulp.tasking.constants import TASKING_CONSTANTS as constants
from pulp.tasking import delete_worker


# The import below is not used in this module, but it needs to be kept here. This module is the
# first and only Pulp module to be imported by celerybeat, and by importing pulp.server.logs, it
# configures the celerybeat logging to log as Pulp does.
import pulp.app.logs  # noqa

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
    def run(self):
        """
        The thread entry point. Sleep for FREQUENCY seconds, then call check_celery_processes()

        This method has a try/except block around check_celery_processes() to add durability to
        this background thread.
        """
        _logger.info(_('Worker Timeout Monitor Started'))
        while True:
            time.sleep(constants.CELERY_CHECK_INTERVAL)
            try:
                self.check_celery_processes()
            except Exception as e:
                _logger.error(e)

    def check_celery_processes(self):
        """
        Look for missing Celery processes, log and cleanup as needed.

        To find a missing Celery process, filter the Workers model for entries older than
        utcnow() - WORKER_TIMEOUT_SECONDS. The heartbeat times are stored in native UTC, so this is
        a comparable datetime. For each missing worker found, call delete_worker() synchronously
        for cleanup.

        This method also checks that at least one resource_manager and one scheduler process is
        present. If there are zero of either, log at the error level that Pulp will not operate
        correctly.
        """
        msg = _('Checking if pulp_workers, pulp_celerybeat, or pulp_resource_manager processes '
                'are missing for more than %d seconds') % constants.HEARTBEAT_MAX_AGE
        _logger.debug(msg)
        now = timezone.now()
        oldest_heartbeat_time = now - timedelta(seconds=constants.HEARTBEAT_MAX_AGE)

        for worker in Worker.objects.filter(last_heartbeat__lt=oldest_heartbeat_time):
            msg = _("Worker '%s' has gone missing, removing from list of workers") % worker.name
            _logger.error(msg)

            if worker.name.startswith(constants.CELERYBEAT_WORKER_NAME):
                worker.delete()
            else:
                delete_worker(worker.name)

        worker_count = Worker.objects.exclude(
            name__startswith=constants.RESOURCE_MANAGER_WORKER_NAME).exclude(
            name__startswith=constants.CELERYBEAT_WORKER_NAME).count()

        scheduler_count = Worker.objects.filter(
            name__startswith=constants.CELERYBEAT_WORKER_NAME).count()

        resource_manager_count = Worker.objects.filter(
            name__startswith=constants.RESOURCE_MANAGER_WORKER_NAME).count()

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
    # the superclass reads this attribute, which is the maximum number of seconds
    # that will ever elapse before the scheduler looks for new or changed schedules.
    max_interval = constants.CELERYBEAT_MAX_SLEEP_INTERVAL

    def __init__(self, *args, **kwargs):
        """
        Initialize the Scheduler object.

        __init__ may be called multiple times because of the lazy instantiation behavior of Celery.
        If a keyword argument named 'lazy' is set to False, this instantiation is the 'real' one,
        and should create the necessary pulp helper threads using spawn_pulp_monitor_threads().
        """
        self._schedule = None
        self._loaded_from_db_count = 0

        # Setting the celerybeat name
        self.celerybeat_name = constants.CELERYBEAT_WORKER_NAME + "@" + platform.node()

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

        # this is not an event that gets sent anywhere. We process it
        # immediately.
        scheduler_event = {
            'timestamp': time.time(),
            'local_received': time.time(),
            'type': 'scheduler-event',
            'hostname': self.celerybeat_name
        }

        worker_watcher.handle_worker_heartbeat(scheduler_event)

        old_timestamp = datetime.utcnow() - timedelta(seconds=constants.CELERYBEAT_LOCK_MAX_AGE)

        # Updating the current lock if lock is on this instance of celerybeat
        try:
            celerybeat_lock = TaskLock.objects.get(name=self.celerybeat_name)
            celerybeat_lock.timestamp = timezone.now()
            celerybeat_lock.save()
            # If current instance has lock and updated lock_timestamp, call super
            _logger.debug(_('Lock updated by %(celerybeat_name)s')
                          % {'celerybeat_name': self.celerybeat_name})
            ret = self.call_tick(self, self.celerybeat_name)
        except TaskLock.DoesNotExist:
            TaskLock.objects.filter(lock=TaskLock.CELERY_BEAT, timestamp__lte=old_timestamp).delete()
            try:
                # Insert new lock entry
                TaskLock.objects.create(name=self.celerybeat_name, lock=TaskLock.CELERY_BEAT)
                _logger.info(_("New lock acquired by %(celerybeat_name)s") %
                             {'celerybeat_name': self.celerybeat_name})
                # After acquiring new lock call super to dispatch tasks
                ret = self.call_tick(self, self.celerybeat_name)

            except IntegrityError:
                # Setting a default wait time for celerybeat instances with no lock
                ret = constants.CELERYBEAT_LOCK_RETRY_TIME
                _logger.info(_("Duplicate or new celerybeat Instance, "
                               "ticking again in %(ret)s seconds.")
                             % {'ret': ret})
        return ret

    def add(self, **kwargs):
        """
        This class does not support adding entries in-place. You must add new
        entries to the database, and they will be picked up automatically.
        """
        raise NotImplementedError

    def close(self):
        delete_worker(self.celerybeat_name, normal_shutdown=True)
        super(Scheduler, self).close()
