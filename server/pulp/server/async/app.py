# -*- coding: utf-8 -*-

# This import will load our configs
from pulp.server import config
from pulp.server import initialization
# We need this import so that the Celery setup_logging signal gets registered
from pulp.server import logs
# This import is here so that Celery will find our application instance
from pulp.server.async.celery_instance import celery


initialization.initialize()