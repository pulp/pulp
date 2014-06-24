# -*- coding: utf-8 -*-

from celery.signals import worker_process_init

# This import will load our configs
from pulp.server import config
from pulp.server.initialization import initialize

# This import is here to register the signal handler of celery.signal.setup_logging
# Removing this import will cause Pulp logging of Celery logs to stop working
import pulp.server.logs

# This import is here so that Celery will find our application instance
from pulp.server.async.celery_instance import celery

@worker_process_init.connect
def init_app(*args, **kwargs):
    initialize()