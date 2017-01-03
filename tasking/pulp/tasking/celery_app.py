"""
This module is the Pulp Celery App. It is passed to the workers from the command line, and they
will see the "celery" module attribute and use it. This module also initializes the Pulp app after
Celery setup finishes.
"""

import contextlib
import logging
import signal
import sys
import time
from gettext import gettext as _

from celery.signals import celeryd_after_setup
from django.db.utils import IntegrityError

# This import is here so that Celery will find our application instance. It's important that other
# Pulp and Django code not get used until after the Celery app is instantiated and does its "fixup"
# of Django.
from pulp.tasking.celery_instance import celery  # noqa
from pulp.tasking.constants import TASKING_CONSTANTS
from pulp.tasking.services import storage
from pulp.tasking.services.worker_watcher import delete_worker

celery.autodiscover_tasks()


_logger = logging.getLogger(__name__)


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
    delete_worker(sender, normal_shutdown=True)

    storage.delete_worker_working_directory(sender)
    storage.create_worker_working_directory(sender)

    if sender.startswith(TASKING_CONSTANTS.RESOURCE_MANAGER_WORKER_NAME):
        get_resource_manager_lock(sender)


def get_resource_manager_lock(name):
    """Block until the the resource manager lock is acquired.

    Tries to acquire the resource manager lock. If the lock cannot be acquired immediately, it
    will wait until the currently active instance becomes unavailable, at which point the worker
    cleanup routine will clear the lock for us to acquire. A worker record will be created so that
    the waiting resource manager will appear in the Status API. We override the SIGTERM signal
    handler so that that the worker record will be immediately cleaned up if the process is killed
    while in this states.

    :param name:   The hostname of the worker
    :type  name:   basestring
    """
    from pulp.app.models.task import TaskLock, Worker
    assert name.startswith(TASKING_CONSTANTS.RESOURCE_MANAGER_WORKER_NAME)

    lock = TaskLock(name=name, lock=TaskLock.RESOURCE_MANAGER)
    worker, created = Worker.objects.get_or_create(name=name)

    with custom_sigterm_handler(name):
        # Whether this is the first lock availability check for this instance
        _first_check = True

        while True:
            worker.save_heartbeat()

            try:
                lock.save()
            except IntegrityError:
                # Only log the message the first time
                if _first_check:
                    msg = _("Resource manager '%s' attempted to acquire the the resource manager "
                            "lock but was unable to do so. It will retry every %d seconds until "
                            "the lock can be acquired." % (
                                name, TASKING_CONSTANTS.CELERY_CHECK_INTERVAL))
                    _logger.info(msg)
                    _first_check = False

                time.sleep(TASKING_CONSTANTS.CELERY_CHECK_INTERVAL)
            else:
                msg = _("Resource manager '%s' has acquired the resource manager lock" % name)
                _logger.info(msg)
                break


@contextlib.contextmanager
def custom_sigterm_handler(name):
    """
    Temporarily installs a custom SIGTERM handler that performs cleanup of the worker record with
    the provided name. Resets the signal handler to the default one after leaving.

    :param name:   The hostname of the worker
    :type  name:   basestring
    """
    def sigterm_handler(_signo, _stack_frame):
        msg = _("Worker '%s' shutdown" % name)
        _logger.info(msg)
        delete_worker(name, normal_shutdown=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, sigterm_handler)
    yield
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
