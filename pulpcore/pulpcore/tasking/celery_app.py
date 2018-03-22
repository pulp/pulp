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
from celery.signals import celeryd_after_setup
from django.db.utils import IntegrityError
from django.utils import timezone

# This import is here so that Celery will find our application instance. It's important that other
# Pulp and Django code not get used until after the Celery app is instantiated and does its "fixup"
# of Django.
from pulpcore.tasking.celery_instance import celery  # noqa
from pulpcore.tasking.constants import TASKING_CONSTANTS
from pulpcore.tasking.services.storage import WorkerDirectory

celery.autodiscover_tasks()


_logger = logging.getLogger(__name__)


class PulpWorkerStep(bootsteps.StartStopStep):
    """
    Adds pulp recurrent logic to celery workers.

    This class is a celery "Blueprint". It extends the functionality of the celery
    consumer by establishing a timer on consumer startup which calls the '_on_tick()'
    method periodically. This allows each worker to write its own worker record to the
    database.

    http://docs.celeryproject.org/en/master/userguide/extending.html
    https://groups.google.com/d/msg/celery-users/3fs0ocREYqw/C7U1lCAp56sJ

    Args:
        consumer (celery.worker.consumer.Consumer): The consumer instance (unused)
    """

    def __init__(self, consumer, **kwargs):
        """
        Create variable for timer reference.

        The step init is called when the consumer instance is created, It is called with the
        consumer instance as the first argument and all keyword arguments from the original
        consumer.__init__ call.

        Args:
            consumer (celery.worker.consumer.Consumer): The consumer instance (unused)
        """
        self.timer_ref = None

    def start(self, consumer):
        """
        Create a timer which periodically runs the on_tick routine.

        This method is called when the worker starts up and also whenever the AMQP connection is
        reset (which triggers an internal restart). The timer is reset when the connection is lost,
        so we have to install the timer again for every call to self.start.

        Args:
            consumer (celery.worker.consumer.Consumer): The consumer instance (unused)
        """
        from pulpcore.tasking.services.worker_watcher import mark_worker_online

        self.timer_ref = consumer.timer.call_repeatedly(
            TASKING_CONSTANTS.PULP_PROCESS_HEARTBEAT_INTERVAL,
            self._on_tick,
            (consumer, ),
            priority=10,
        )
        mark_worker_online(consumer.hostname)
        self._on_tick(consumer)

    def stop(self, consumer):
        """
        Stop the timer when the worker is stopped.

        This method is called every time the worker is restarted (i.e. connection is lost)
        and also at shutdown.

        Args:
            consumer (celery.worker.consumer.Consumer): The consumer instance (unused)
        """
        if self.timer_ref:
            self.timer_ref.cancel()
            self.timer_ref = None

    def shutdown(self, consumer):
        """
        Called when a worker is shutdown.
        So far, this just marks the worker as offline.

        Args:
            consumer (celery.worker.consumer.Consumer): The consumer instance (unused)
        """
        from pulpcore.tasking.services.worker_watcher import mark_worker_offline

        # Mark the worker as offline
        mark_worker_offline(consumer.hostname, normal_shutdown=True)

    def _on_tick(self, consumer):
        """
        This method regularly checks for offline workers and records worker heartbeats

        Args:
            consumer (celery.worker.consumer.Consumer): The consumer instance (unused)
        """
        from pulpcore.tasking.services.worker_watcher import (check_celery_processes,
                                                              handle_worker_heartbeat)

        check_celery_processes()
        handle_worker_heartbeat(consumer.hostname)


celery.steps['consumer'].add(PulpWorkerStep)


@celeryd_after_setup.connect
def initialize_worker(sender, instance, **kwargs):
    """
    This function performs all the necessary initialization of the Celery worker.

    We clean up old state in case this worker was previously running, but died unexpectedly.
    In such cases, any Pulp tasks that were running or waiting on this worker will show incorrect
    state. Any reserved_resource reservations associated with the previous worker will also be
    removed along with the setting of online=False on the worker record in the database itself.
    The working directory specified in /etc/pulp/server.conf (/var/lib/pulp/tmp/<worker_name>)
    by default is removed and recreated. This is called early in the worker start process,
    and later when it's fully online. If there is no previous work to cleanup, this method still
    runs, but has no effect on the database.

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

    Args:
        sender (str): The hostname of the worker
        instance (celery.apps.worker.Worker) The Worker instance to be initialized (unused)
        kwargs (dict): (unused)
    """
    from pulpcore.tasking.services.worker_watcher import mark_worker_offline

    # Mark if present old instance of worker as offline
    mark_worker_offline(sender, normal_shutdown=True)

    working_dir = WorkerDirectory(sender)
    working_dir.delete()
    working_dir.create()

    if sender.startswith(TASKING_CONSTANTS.RESOURCE_MANAGER_WORKER_NAME):
        get_resource_manager_lock(sender)


def get_resource_manager_lock(name):
    """Block until the the resource manager lock is acquired.
    Tries to acquire the resource manager lock.

    If the lock cannot be acquired immediately, it will wait until the
    currently active instance becomes unavailable, at which point the worker
    cleanup routine will clear the lock for us to acquire. A worker record will
    be created so that the waiting resource manager will appear in the Status
    API. This worker record will be cleaned up through the regular worker
    shutdown routine.

    Args:
        name (str): The hostname of the worker
    """
    from pulpcore.app.models.task import TaskLock, Worker

    assert name.startswith(TASKING_CONSTANTS.RESOURCE_MANAGER_WORKER_NAME)

    lock = TaskLock(name=name, lock=TaskLock.RESOURCE_MANAGER)
    worker, created = Worker.objects.get_or_create(name=name)
    worker.save_heartbeat()

    # Whether this is the first lock availability check for this instance
    _first_check = True

    while True:

        now = timezone.now()
        old_timestamp = now - timedelta(seconds=TASKING_CONSTANTS.PULP_PROCESS_TIMEOUT_INTERVAL)

        TaskLock.objects.filter(lock=TaskLock.RESOURCE_MANAGER,
                                timestamp__lte=old_timestamp).delete()

        # Update the worker record so that Pulp knows we exist
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
