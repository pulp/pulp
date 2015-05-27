"""
This module is the Pulp Celery App. It is passed to the workers from the command line, and they
will see the "celery" module attribute and use it. This module also initializes the Pulp app after
Celery setup finishes.
"""
from celery.signals import worker_init

# This import will load our configs
from pulp.server import config  # noqa
from pulp.server import initialization
# We need this import so that the Celery setup_logging signal gets registered
from pulp.server import logs  # noqa
from pulp.server.async import tasks
# This import is here so that Celery will find our application instance
from pulp.server.async.celery_instance import celery  # noqa
from pulp.server.managers.repo import _common as common_utils


@worker_init.connect
def initialize_worker(sender, instance, **kwargs):
    """
    This function performs all the necessary initialization of the Celery worker.

    It starts by cleaning up old state if this worker was previously running, but died unexpectedly.
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

    name = sender
    tasks._delete_worker(name, normal_shutdown=True)

    # Create a new working directory for worker that is starting now
    common_utils.create_worker_working_directory(name)
