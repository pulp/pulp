"""
This module is the Pulp Celery App. It is passed to the workers from the command line, and they
will see the "celery" module attribute and use it. This module also initializes the Pulp app after
Celery setup finishes.
"""
from celery.signals import celeryd_after_setup

# This import will load our configs
from pulp.server import config  # noqa
from pulp.server import initialization
# We need this import so that the Celery setup_logging signal gets registered
from pulp.server import logs  # noqa
# This import is here so that Celery will find our application instance
from pulp.server.async.celery_instance import celery  # noqa


@celeryd_after_setup.connect
def initialize_pulp(sender, instance, **kwargs):
    """
    This function makes the call to Pulp's initialization code. It uses the celeryd_after_setup
    signal[0] so that it gets called by Celery after logging is initialized, but before Celery
    starts to run tasks.

    [0] http://celery.readthedocs.org/en/latest/userguide/signals.html#celeryd-after-setup

    :param sender:   The hostname of the worker (unused)
    :type  sender:   basestring
    :param instance: The Worker instance to be initialized (unused)
    :type  instance: celery.apps.worker.Worker
    :param kwargs:   Other params (unused)
    :type  kwargs:   dict
    """
    initialization.initialize()
