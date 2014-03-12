# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import logging
import sys

# We need to initialize logging early, because some of the other imports in this module can generate
# log messages.
from pulp.server import logs
logs.start_logging()

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
        msg  = 'One or more plugins failed to initialize. If a new type has '
        msg += 'been added, run pulp-manage-db to load the type into the '
        msg += 'database and restart the application. '
        msg += 'Error message: %s' % str(e)
        raise InitializationException(msg), None, sys.exc_info()[2]

    # Load the mappings of manager type to managers
    manager_factory.initialize()

    _IS_INITIALIZED = True
