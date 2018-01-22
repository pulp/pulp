"""
This module is the Pulp Celery App. It is passed to the workers from the command line, and they
will see the "celery" module attribute and use it. This module also initializes the Pulp app after
Celery setup finishes.
"""

import logging
import time
from datetime import datetime, timedelta
from gettext import gettext as _

from celery import bootsteps
from celery.signals import celeryd_after_setup, worker_process_init
import mongoengine

from pulp.common import constants, dateutils
from pulp.server import initialization
from pulp.server.async import tasks, worker_watcher
from pulp.server.constants import PULP_PROCESS_HEARTBEAT_INTERVAL, PULP_PROCESS_TIMEOUT_INTERVAL
from pulp.server.db.model import Worker, ResourceManagerLock
from pulp.server.db.connection import reconnect
from pulp.server.managers.repo import _common as common_utils

# This import will load our configs
from pulp.server import config  # noqa
# We need this import so that the Celery setup_logging signal gets registered
from pulp.server import logs  # noqa
# This import is here so that Celery will find our application instance
from pulp.server.async.celery_instance import celery  # noqa

import pulp.server.tasks  # noqa

_logger = logging.getLogger(__name__)


class HeartbeatStep(bootsteps.StartStopStep):
    """
    Adds pulp heartbeat updating to celery workers.

    This class is a celery "Blueprint". It extends the functionality of the celery
    worker by establishing a timer on consumer startup which calls the '_record_heartbeat()'
    method periodically. This allows each worker to write its own worker record to the
    database, instead of relying on pulp_celerybeat to do so.

    We also use this bootstep to perform initialization of the pulp worker as well as
    cleanup of previous workers who might have died unexpectedly.

    http://docs.celeryproject.org/en/master/userguide/extending.html
    https://groups.google.com/d/msg/celery-users/3fs0ocREYqw/C7U1lCAp56sJ
    """

    def __init__(self, consumer, **kwargs):
        """
        Create variable for timer reference and set up database connections and
        other initialization functions.

        The step init is called when the consumer instance is created, It is called with the
        consumer instance as the first argument and all keyword arguments from the original
        consumer.__init__ call.

        :param consumer: The consumer instance (unused)
        :type  consumer: celery.worker.consumer.Consumer
        """
        self.timer_ref = None
        self.first_start = True
        initialization.initialize()

    def start(self, consumer):
        """
        Create a timer which periodically runs the heartbeat routine. Delete any stale worker data.

        This method is called when the worker starts up and also whenever the AMQP connection is
        reset (which triggers an internal restart). The timer is reset when the connection is lost,
        so we have to install the timer again for every call to self.start.

        We are using this to deleting any stale worker data from improperly killed workers.
        We need to do this here, because if this happens any earlier in the process, the task
        revokation inside of _delete_worker() will cause the process to lock up. However, since
        this method runs every time the consumer restarts, and we don't want to delete stale
        worker data every time that happens, set a guard variable so that it only happens once.

        :param consumer: The consumer instance
        :type  consumer: celery.worker.consumer.Consumer
        """
        self.timer_ref = consumer.timer.call_repeatedly(
            PULP_PROCESS_HEARTBEAT_INTERVAL,
            self._record_heartbeat,
            (consumer, ),
            priority=10,
        )
        self._record_heartbeat(consumer)

        # Delete any potential old worker state
        if self.first_start:
            tasks._delete_worker(consumer.hostname, normal_shutdown=True)

            # Create a new working directory for worker that is starting now
            # The working directory is specified in /etc/pulp/server.conf
            # (/var/cache/pulp/<worker_name>
            common_utils.delete_worker_working_directory(consumer.hostname)
            common_utils.create_worker_working_directory(consumer.hostname)

        self.first_start = False

    def stop(self, consumer):
        """
        Stop the timer when the worker is stopped.

        This method is called every time the worker is restarted (i.e. connection is lost)
        and also at shutdown.

        :param consumer: The consumer instance (unused)
        :type  consumer: celery.worker.consumer.Consumer
        """
        if self.timer_ref:
            self.timer_ref.cancel()
            self.timer_ref = None

    def shutdown(self, consumer):
        """
        Called when the consumer is shut down.

        So far, this just cleans up the database by removing the worker's record in
        the workers collection.

        :param consumer: The consumer instance
        :type  consumer: celery.worker.consumer.Consumer
        """
        tasks._delete_worker(consumer.hostname, normal_shutdown=True)

    def _record_heartbeat(self, consumer):
        """
        This method creates or updates the worker record

        :param consumer: The consumer instance
        :type  consumer: celery.worker.consumer.Consumer
        """
        name = consumer.hostname
        # Update the worker record timestamp and handle logging new workers
        worker_watcher.handle_worker_heartbeat(name)

        # If the worker is a resource manager, update the associated ResourceManagerLock timestamp
        if name.startswith(constants.RESOURCE_MANAGER_WORKER_NAME):
            ResourceManagerLock.objects(name=name).update_one(set__timestamp=datetime.utcnow(),
                                                              upsert=False)


celery.steps['consumer'].add(HeartbeatStep)


@celeryd_after_setup.connect
def wait_for_manager_lock(sender, instance, **kwargs):
    """
    We use the celeryd_after_setup signal[0] so that it gets called by Celery after logging is
    initialized, but before Celery starts to run tasks.

    If the worker is a resource manager, it tries to acquire a lock stored within the database.
    If the lock cannot be acquired immediately, it will wait until the currently active instance
    becomes unavailable, at which point the worker cleanup routine will clear the lock for us to
    acquire. While the worker remains in this waiting state, it is not connected to the broker and
    will not attempt to do any work.

    [0] http://celery.readthedocs.org/en/latest/userguide/signals.html#celeryd-after-setup

    :param sender:   The hostname of the worker
    :type  sender:   basestring
    :param instance: The Worker instance to be initialized (unused)
    :type  instance: celery.apps.worker.Worker
    :param kwargs:   Other params (unused)
    :type  kwargs:   dict
    """

    # If the worker is a resource manager, try to acquire the lock, or wait until it
    # can be acquired
    if sender.startswith(constants.RESOURCE_MANAGER_WORKER_NAME):
        get_resource_manager_lock(sender)


@worker_process_init.connect
def reconnect_services(sender, **kwargs):
    """
    Reconnect any services that were established before a worker forks its child process
    """
    reconnect()


def get_resource_manager_lock(name):
    """
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
    assert name.startswith(constants.RESOURCE_MANAGER_WORKER_NAME)

    lock = ResourceManagerLock(name=name)

    # Whether this is the first lock availability check for this instance
    _first_check = True

    while True:

        now = dateutils.ensure_tz(datetime.utcnow())
        old_timestamp = now - timedelta(seconds=PULP_PROCESS_TIMEOUT_INTERVAL)

        ResourceManagerLock.objects(timestamp__lte=old_timestamp).delete()

        # Create / update the worker record so that Pulp knows we exist
        Worker.objects(name=name).update_one(set__last_heartbeat=datetime.utcnow(),
                                             upsert=True)
        try:
            lock.timestamp = now
            lock.save()

            msg = _("Resource manager '%s' has acquired the resource manager lock") % name
            _logger.debug(msg)

            if not _first_check:
                msg = _("Failover occurred: '%s' is now the primary resource manager") % name
                _logger.warning(msg)

            break
        except mongoengine.NotUniqueError:
            # Only log the message the first time
            if _first_check:
                _logger.info(_("Hot spare pulp_resource_manager instance '%(name)s' detected.")
                             % {'name': name})
                _first_check = False

            time.sleep(PULP_PROCESS_HEARTBEAT_INTERVAL)
