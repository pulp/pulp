"""
This module is the Pulp Celery App. It is passed to the workers from the command line, and they
will see the "celery" module attribute and use it. This module also initializes the Pulp app after
Celery setup finishes.
"""
import time
import logging
import platform
import mongoengine

from gettext import gettext as _
from datetime import datetime
from celery.signals import celeryd_after_setup

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


@celeryd_after_setup.connect
def initialize_worker(sender, instance, **kwargs):
    """
    This function performs all the necessary initialization of the Celery worker.

    If the worker is a resource manager, it tries to acquire a lock stored within the database.
    This prevents more than one resource manager from attempting to act concurrently.  If the lock
    cannot be acquired immediately, it will wait until the currently active instance becomes
    unavailable, at which point the worker cleanup routine will clear the lock for us to acquire.

    We also clean up old state in case this worker was previously running, but died unexpectedly.
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

    [0] http://celery.readthedocs.org/en/latest/userguide/signals.html#celeryd-after-setup

    :param sender:   The hostname of the worker
    :type  sender:   basestring
    :param instance: The Worker instance to be initialized (unused)
    :type  instance: celery.apps.worker.Worker
    :param kwargs:   Other params (unused)
    :type  kwargs:   dict
    """
    initialization.initialize()

    # Whether this instance has had to wait for availability
    _cycled = False

    # If the worker is a resource manager, try to acquire the lock, or wait until it
    # can be acquired
    if sender.startswith(constants.RESOURCE_MANAGER_WORKER_NAME):

        name = constants.RESOURCE_MANAGER_WORKER_NAME + "@" + platform.node()
        lock = ResourceManagerLock(name=name)

        while True:

            # Create a worker record so the user can tell that we're running
            Worker.objects(name=sender).update_one(set__last_heartbeat=datetime.utcnow(),
                                                   upsert=True)

            try:
                lock.save()

                if _cycled:
                    msg = _("A new instance of pulp_resource_manager '%s' has become "
                            "active after previous instance no longer available") % sender
                    _logger.info(msg)

                break
            except mongoengine.NotUniqueError:
                if not _cycled:
                    msg = _("An instance of pulp_resource_manager is already active. "
                            "Halting execution until the currently active "
                            "resource_manager becomes unavailable.")
                    _logger.info(msg)
                    _cycled = True

                time.sleep(constants.CELERY_CHECK_INTERVAL)

    # Delete any potential old state
    tasks._delete_worker(sender, normal_shutdown=True)

    # Create a new working directory for worker that is starting now
    common_utils.delete_worker_working_directory(sender)
    common_utils.create_worker_working_directory(sender)
