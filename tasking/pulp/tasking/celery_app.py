"""
This module is the Pulp Celery App. It is passed to the workers from the command line, and they
will see the "celery" module attribute and use it. This module also initializes the Pulp app after
Celery setup finishes.
"""

import logging

import time
from datetime import timedelta
from gettext import gettext as _

from celery import bootsteps
from celery.signals import celeryd_after_setup, worker_shutdown
from django.db.utils import IntegrityError
from django.utils import timezone

# This import is here so that Celery will find our application instance. It's important that other
# Pulp and Django code not get used until after the Celery app is instantiated and does its "fixup"
# of Django.
from pulp.app.models.task import TaskLock, Worker
from pulp.tasking.celery_instance import celery  # noqa
from pulp.tasking.constants import TASKING_CONSTANTS
from pulp.tasking.services import storage, worker_watcher

celery.autodiscover_tasks()


_logger = logging.getLogger(__name__)


class HeartbeatStep(bootsteps.StartStopStep):
    """
    Adds pulp heartbeat updating to celery workers.

    This class is a celery "Blueprint". It extends the functionality of the celery
    worker by establishing a timer on worker startup which calls the '_record_heartbeat()'
    method periodically. This allows each worker to write its own worker record to the
    database, instead of relying on pulp_celerybeat to do so.

    http://docs.celeryproject.org/en/master/userguide/extending.html
    https://groups.google.com/d/msg/celery-users/3fs0ocREYqw/C7U1lCAp56sJ

    :param worker: The worker instance (unused)
    :type  worker: celery.apps.worker.Worker
    """

    requires = ('celery.worker.components:Timer', )

    def __init__(self, worker, **kwargs):
        """
        Create variable for timer reference.

        The step init is called when the worker instance is created, It is called with the
        worker instance as the first argument and all keyword arguments from the original
        worker.__init__ call.

        :param worker: The worker instance (unused)
        :type  worker: celery.apps.worker.Worker
        """
        self.timer_ref = None

    def start(self, worker):
        """
        Create a timer which periodically runs the heartbeat routine.

        This method is called when the worker starts up and also whenever the AMQP connection is
        reset (which triggers an internal restart). The timer is reset when the connection is lost,
        so we have to install the timer again for every call to self.start.

        :param worker: The worker instance
        :type  worker: celery.apps.worker.Worker
        """
        self.timer_ref = worker.timer.call_repeatedly(
            TASKING_CONSTANTS.PULP_PROCESS_HEARTBEAT_INTERVAL,
            self._record_heartbeat,
            (worker, ),
            priority=10,
        )
        self._record_heartbeat(worker)

    def stop(self, worker):
        """
        Stop the timer when the worker is stopped.

        This method is called every time the worker is restarted (i.e. connection is lost)
        and also at shutdown.

        :param worker: The worker instance (unused)
        :type  worker: celery.apps.worker.Worker
        """
        if self.timer_ref:
            self.timer_ref.cancel()
            self.timer_ref = None

    def terminate(self, worker):
        """
        Clean up the worker record and log when the celery worker is terminated.

        :param worker: The worker instance
        :type  worker: celery.apps.worker.Worker
        """
        worker_watcher.handle_worker_offline(worker.hostname)

    def _record_heartbeat(self, worker):
        """
        This method creates or updates the worker record

        :param worker: The worker instance
        :type  worker: celery.apps.worker.Worker
        """
        name = worker.hostname
        # Update the worker record timestamp and handle logging new workers
        worker_watcher.handle_worker_heartbeat(name)

        # If the worker is a resource manager, update the associated ResourceManagerLock timestamp
        if name.startswith(TASKING_CONSTANTS.RESOURCE_MANAGER_WORKER_NAME):
            TaskLock.objects(name=name).update(timestamp=datetime.utcnow())


celery.steps['worker'].add(HeartbeatStep)


@celeryd_after_setup.connect
def initialize_worker(sender, instance, **kwargs):
    """
    This function performs all the necessary initialization of the Celery worker.

    We clean up old state in case this worker was previously running, but died unexpectedly.
    In such cases, any Pulp tasks that were running or waiting on this worker will show incorrect
    state. Any reserved_resource reservations associated with the previous worker will also be
    removed along with the worker entry in the database itself. The working directory specified in
    /etc/pulp/server.conf (/var/cache/pulp/<worker_name>) by default is removed and recreated. This
    is called early in the worker start process, and later when it's fully online, pulp_celerybeat
    will discover the worker as usual to allow new work to arrive at this worker. If there is no
    previous work to cleanup, this method still runs, but has no effect on the database.

    After cleaning up old state, it ensures the existence of the worker's working directory.

    Lastly, this function makes the call to Pulp's initialization code.

    It uses the celeryd_after_setup signal[0] so that it gets called by Celery after logging is
    initialized, but before Celery starts to run tasks.

    If the worker is a resource manager, it tries to acquire a lock stored within the database.
    If the lock cannot be acquired immediately, it will wait until the currently active instance
    becomes unavailable, at which point the worker cleanup routine will clear the lock for us to
    acquire. While the worker remains in this waiting state, it is not connected to the broker and
    will not attempt to do any work. A side effect of this is that, if terminated while in this
    state, the process will not send the "worker-offline" signal used by the EventMonitor to
    immediately clean up terminated workers. Therefore, we override the SIGTERM signal handler
    while in this state so that cleanup is done properly.

    [0] http://celery.readthedocs.org/en/latest/userguide/signals.html#celeryd-after-setup

    :param sender:   The hostname of the worker
    :type  sender:   basestring

    :param instance: The Worker instance to be initialized (unused)
    :type  instance: celery.apps.worker.Worker

    :param kwargs:   Other params (unused)
    :type  kwargs:   dict
    """
    # Delete any potential old state
    worker_watcher.delete_worker(sender, normal_shutdown=True)

    storage.delete_worker_working_directory(sender)
    storage.create_worker_working_directory(sender)

    if sender.startswith(TASKING_CONSTANTS.RESOURCE_MANAGER_WORKER_NAME):
        get_resource_manager_lock(sender)


@worker_shutdown.connect
def shutdown_worker(signal, sender):
    """
    Called when a worker is shutdown.
    So far, this just cleans up the database by removing the worker's record in
    the workers collection.

    :param signal:   The signal being sent to the workerTaskLock
    :param type:     int

    :param instance: The hostname of the worker
    :type  instance: celery.apps.worker.Worker
    """
    # Delete any potential old state
    worker_watcher.delete_worker(sender.hostname, normal_shutdown=True)


def get_resource_manager_lock(name):
    """Block until the the resource manager lock is acquired.
    Tries to acquire the resource manager lock.

    If the lock cannot be acquired immediately, it will wait until the
    currently active instance becomes unavailable, at which point the worker
    cleanup routine will clear the lock for us to acquire. A worker record will
    be created so that the waiting resource manager will appear in the Status
    API. This worker record will be cleaned up through the regular worker
    shutdown routine.

    :param name:   The hostname of the worker
    :type  name:   basestring
    """
    assert name.startswith(TASKING_CONSTANTS.RESOURCE_MANAGER_WORKER_NAME)

    lock = TaskLock(name=name, lock=TaskLock.RESOURCE_MANAGER)
    worker, created = Worker.objects.get_or_create(name=name)

    # Whether this is the first lock availability check for this instance
    _first_check = True

    while True:

        now = timezone.now()
        old_timestamp = now - timedelta(seconds=TASKING_CONSTANTS.PULP_PROCESS_TIMEOUT_INTERVAL)

        TaskLock.objects.filter(lock=TaskLock.RESOURCE_MANAGER,
                                timestamp__lte=old_timestamp).delete()

        # Create / update the worker record so that Pulp knows we exist
        worker.save_heartbeat()

        try:
            lock.timestamp = now
            lock.save()

            msg = _("Resource manager '%s' has acquired the resource manager lock") % name
            _logger.debug(msg)

            if not _first_check:
                msg = _("Failover occurred: '%s' is now the primary resource manager") % name
                _logger.warning(msg)

            break
        except IntegrityError:
            # Only log the message the first time
            if _first_check:
                _logger.info(_("Hot spare pulp_resource_manager instance '%(name)s' detected.")
                             % {'name': name})
                _first_check = False

            time.sleep(TASKING_CONSTANTS.PULP_PROCESS_HEARTBEAT_INTERVAL)
