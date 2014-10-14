# -*- coding: utf-8 -*-

from gettext import gettext as _
import logging
import sys

# It is important that we initialize the DB connection early
from pulp.server.db import connection as db_connection
db_connection.initialize()

from pulp.plugins.loader import api as plugin_api
from pulp.server.managers import factory as manager_factory


logger = logging.getLogger(__name__)
_IS_INITIALIZED = False


class InitializationException(Exception):

    def __init__(self, message):
        Exception.__init__(self, message)
        self.message = message


def initialize():
    global _IS_INITIALIZED
    if _IS_INITIALIZED:
        return

    # This is here temporarily, so that we can run the monkey patches for qpid and stuff
    import kombu.transport.qpid

    # Load plugins and resolve against types. This is also a likely candidate
    # for causing the server to fail to start.
    try:
        plugin_api.initialize()
    except Exception, e:
        msg  = _(
            'One or more plugins failed to initialize. If a new type has been added, '
            'run pulp-manage-db to load the type into the database and restart the application. '
            'Error message: %s')
        msg = msg % str(e)
        logger.error(msg)
        raise

    # Load the mappings of manager type to managers
    manager_factory.initialize()

    _IS_INITIALIZED = True
