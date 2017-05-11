import logging
import platform
import threading
import time
from datetime import datetime, timedelta
from gettext import gettext as _

from celery import beat
from django.utils import timezone
from django.db import IntegrityError

from pulpcore.app.models.task import TaskLock, Worker
from pulpcore.tasking.celery_app import celery as app
from pulpcore.tasking.constants import TASKING_CONSTANTS as constants
from pulpcore.tasking.services import worker_watcher


# The import below is not used in this module, but it needs to be kept here. This module is the
# first and only Pulp module to be imported by celerybeat, and by importing pulpcore.app.logs, it
# configures the celerybeat logging to log as Pulp does.
import pulpcore.app.logs  # noqa

_logger = logging.getLogger(__name__)

# setting the celerybeat name
CELERYBEAT_NAME = constants.CELERYBEAT_WORKER_NAME + "@" + platform.node()


class CeleryProcessTimeoutMonitor(threading.Thread):
    """
    A thread dedicated to monitoring Celery processes that have stopped checking in.

    Once a Celery process is determined to be missing it logs and handles cleanup appropriately.
    """
    def run(self):
        """
        The thread entry point. Sleep for the heartbeat interval, then call check_celery_processes()

        This method has a try/except block around check_celery_processes() to add durability to
        this background thread.
        """
        _logger.info(_('Worker Timeout Monitor Started'))
        while True:
            time.sleep(constants.PULP_PROCESS_HEARTBEAT_INTERVAL)
            try:
                self.check_celery_processes()
            except Exception as e:
                _logger.error(e)

    def check_celery_processes(self):
        """
        Look for missing Celery processes, log and cleanup as needed.

        To find a missing Celery process, filter the Workers model for entries older than
        utcnow() - WORKER_TIMEOUT_SECONDS. The heartbeat times are stored in native UTC, so this is
        a comparable datetime. For each missing worker found, call mark_worker_offline()
        synchronously for cleanup.

        This method also checks that at least one resource_manager and one scheduler process is
        present. If there are zero of either, log at the error level that Pulp will not operate
        correctly.
        """
        msg = _('Checking if pulp_workers, pulp_celerybeat, or pulp_resource_manager processes '
                'are missing for more than %d seconds') % constants.PULP_PROCESS_TIMEOUT_INTERVAL
        _logger.debug(msg)
        now = timezone.now()
        oldest_heartbeat_time = now - timedelta(seconds=constants.PULP_PROCESS_TIMEOUT_INTERVAL)

        for worker in Worker.objects.filter(last_heartbeat__lt=oldest_heartbeat_time, online=True):
            msg = _("Worker '%s' has gone missing, removing from list of workers") % worker.name
            _logger.error(msg)

            worker_watcher.mark_worker_offline(worker.name)

        worker_count = Worker.objects.exclude(
            name__startswith=constants.RESOURCE_MANAGER_WORKER_NAME).exclude(
            name__startswith=constants.CELERYBEAT_WORKER_NAME).filter(online=True).count()

        scheduler_count = Worker.objects.filter(
            name__startswith=constants.CELERYBEAT_WORKER_NAME).filter(online=True).count()

        resource_manager_count = Worker.objects.filter(
            name__startswith=constants.RESOURCE_MANAGER_WORKER_NAME).filter(online=True).count()

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
    max_interval = constants.PULP_PROCESS_HEARTBEAT_INTERVAL

    def __init__(self, *args, **kwargs):
        """
        Initialize the Scheduler object.

        __init__ may be called multiple times because of the lazy instantiation behavior of Celery.
        If a keyword argument named 'lazy' is set to False, this instantiation is the 'real' one,
        and should create the necessary pulp helper threads using spawn_pulp_monitor_threads().
        """
        self._schedule = None
        self._loaded_from_db_count = 0
        self._first_lock_acq_check = True

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

        A WorkerTimeoutMonitor thread is started that watches for cases where all workers
        disappear at once.

        The thread is set with daemon = True so that if the main thread exits, it will close
        automatically.

        This method should be called only in certain situations, see docstrings on the object for
        more details.
        """
        # start monitoring workers who may timeout
        worker_timeout_monitor = CeleryProcessTimeoutMonitor()
        worker_timeout_monitor.daemon = True
        worker_timeout_monitor.start()

    def call_tick(self, celerybeat_name):
        """
        Call the superclass tick method and log a debug message.

        :param celerybeat_name: hostname of the celerybeat instance
        :type  celerybeat_name: basestring

        :return:                seconds until the next tick
        :rtype:                 integer
        """
        ret = super(Scheduler, self).tick()
        _logger.debug(_("%(celerybeat_name)s will tick again in %(ret)s secs")
                      % {'ret': ret, 'celerybeat_name': celerybeat_name})
        return ret

    def tick(self):
        """
        Superclass runs a tick, that is one iteration of the scheduler. Executes all due tasks.

        This method updates the last heartbeat time of the scheduler.

        :return:    number of seconds before the next tick should run
        :rtype:     float
        """
        worker_watcher.handle_worker_heartbeat(CELERYBEAT_NAME)

        now = timezone.now()
        old_timestamp = now - timedelta(seconds=constants.PULP_PROCESS_TIMEOUT_INTERVAL)

        # Updating the current lock if lock is on this instance of celerybeat
        try:
            celerybeat_lock = TaskLock.objects.get(name=CELERYBEAT_NAME)
            celerybeat_lock.timestamp = timezone.now()
            celerybeat_lock.save()
            # If current instance has lock and updated lock_timestamp, call super

            _logger.debug(_('Lock updated by %(celerybeat_name)s')
                          % {'celerybeat_name': CELERYBEAT_NAME})
            ret = self.call_tick(CELERYBEAT_NAME)
        except TaskLock.DoesNotExist:
            TaskLock.objects.filter(lock=TaskLock.CELERY_BEAT,
                                    timestamp__lte=old_timestamp).delete()

            try:
                # Insert new lock entry
                lock_timestamp = datetime.utcnow()
                TaskLock.objects.create(name=CELERYBEAT_NAME, lock=TaskLock.CELERY_BEAT,
                                        timestamp=lock_timestamp)

                _logger.debug(_("New lock acquired by %(celerybeat_name)s") %
                              {'celerybeat_name': CELERYBEAT_NAME})

                if not self._first_lock_acq_check:
                    msg = _("Failover occurred: '%s' is now the primary celerybeat "
                            "instance") % CELERYBEAT_NAME
                    _logger.warning(msg)

                # After acquiring new lock call super to dispatch tasks
                ret = self.call_tick(CELERYBEAT_NAME)

            except IntegrityError:
                # Setting a default wait time for celerybeat instances with no lock
                ret = constants.PULP_PROCESS_HEARTBEAT_INTERVAL

                if self._first_lock_acq_check:
                    _logger.info(_("Hot spare celerybeat instance '%(celerybeat_name)s' detected.")
                                 % {'celerybeat_name': CELERYBEAT_NAME})

        self._first_lock_acq_check = False
        return ret

    def add(self, **kwargs):
        """
        This class does not support adding entries in-place. You must add new
        entries to the database, and they will be picked up automatically.
        """
        raise NotImplementedError

    def close(self):
        """This is called when celerybeat is being shutdown."""
        worker_watcher.handle_worker_offline(CELERYBEAT_NAME)
        super(Scheduler, self).close()
