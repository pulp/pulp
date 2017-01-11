"""
This module is the Pulp Celery App. It is passed to the workers from the command line, and they
will see the "celery" module attribute and use it. This module also initializes the Pulp app after
Celery setup finishes.
"""

import logging
import time
from datetime import datetime
from gettext import gettext as _

import mongoengine
from celery import bootsteps
from celery.signals import celeryd_after_setup, worker_shutdown

from pulp.common import constants
from pulp.server import initialization
from pulp.server.async import tasks
from pulp.server.db.model import ResourceManagerLock, Worker
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

    requires = ('celery.worker.components:Timer', )

    def __init__(self, consumer, **kwargs):
        """
        The step init is called when the Consumer instance is created, It is called with the
        consumer instance as the first argument and all keyword arguments from the original
        Consumer.__init__ call.
        """
        self.tref = None

    def start(self, consumer):
        """
        This method is called when the worker starts up and also whenever the AMQP connection is
        reset (which triggers an internal restart). The timer is reset when the connection is lost,
        so we have to install the timer again for every call to self.start.
        """
        self.tref = consumer.timer.call_repeatedly(
            30.0, self.record_heartbeat, (consumer, ), priority=10,
        )
        self.record_heartbeat(consumer)

    def stop(self, consumer):
        # the Consumer calls stop every time the consumer is restarted (i.e. connection is lost)
        # and also at shutdown.  The Worker will call stop at shutdown only.
        if self.tref:
            self.tref.cancel()
            self.tref = None

    def shutdown(self, consumer):
        # shutdown is called by the Consumer at shutdown, it's not
        # called by Worker.
        tasks._delete_worker(consumer.hostname, normal_shutdown=True)

    def record_heartbeat(self, consumer):
        timestamp = datetime.utcnow()
        Worker.objects(name=consumer.hostname).\
            update_one(set__last_heartbeat=timestamp, upsert=True)


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
    initialization.initialize()

    # Delete any potential old state
    tasks._delete_worker(sender, normal_shutdown=True)

    # Create a new working directory for worker that is starting now
    common_utils.delete_worker_working_directory(sender)
    common_utils.create_worker_working_directory(sender)

    # If the worker is a resource manager, try to acquire the lock, or wait until it
    # can be acquired
    if sender.startswith(constants.RESOURCE_MANAGER_WORKER_NAME):
        get_resource_manager_lock(sender)


@worker_shutdown.connect
def shutdown_worker(signal, sender):
    """
    Called when a worker is shutdown.

    So far, this just cleans up the database by removing the worker's record in
    the workers collection.

    :param signal:   The signal being sent to the worker
    :type  signal:   int
    :param instance: The hostname of the worker
    :type  instance: celery.apps.worker.Worker
    """
    tasks._delete_worker(sender.hostname, normal_shutdown=True)


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
        # Create / update the worker record so that Pulp knows we exist
        Worker.objects(name=name).update_one(set__last_heartbeat=datetime.utcnow(),
                                             upsert=True)
        try:
            lock.save()

            msg = _("Resource manager '%s' has acquired the resource manager lock") % name
            _logger.info(msg)
            break
        except mongoengine.NotUniqueError:
            # Only log the message the first time
            if _first_check:
                msg = _("Resource manager '%(name)s' attempted to acquire the the resource manager "
                        "lock but was unable to do so. It will retry every %(interval)d seconds "
                        "until the lock can be acquired.") % \
                    {'name': name, 'interval': constants.CELERY_CHECK_INTERVAL}
                _logger.info(msg)
                _first_check = False

            time.sleep(constants.CELERY_CHECK_INTERVAL)
