"""
This module is the Pulp Celery App. It is passed to the workers from the command line, and they
will see the "celery" module attribute and use it. This module also initializes the Pulp app after
Celery setup finishes.
"""

import contextlib
import logging
import sys
import signal
from gettext import gettext as _

from celery.signals import celeryd_after_setup

from pulp.tasking import delete_worker


# This import is here so that Celery will find our application instance
from pulp.tasking.celery_instance import celery  # noqa

# This import is here so Celery will discover all tasks
import pulp.tasking.registry  # noqa


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
