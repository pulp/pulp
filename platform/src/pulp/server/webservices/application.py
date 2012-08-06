# -*- coding: utf-8 -*-
#
# Copyright © 2010-2012 Red Hat, Inc.
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

# XXX monkey patching web.py YUCK!
# This keeps the web.py wsgi app from trying to handle otherwise unhandled
# exceptions and lets Pulp error handling middleware handle them instead
# This exists here as it is the first place that Pulp imports web.py, so all
# web.py applications will be instantiated *after* their base class is patched
def _handle_with_processors(self):
    def process(processors):
        if processors:
            p, processors = processors[0], processors[1:]
            return p(lambda : process(processors))
        else:
            return self.handle()
    return process(self.processors)

import web

web.application.handle_with_processors = _handle_with_processors


from pulp.server import config # automatically loads config
from pulp.server import logs
from pulp.server.db import connection as db_connection

# We need to read the config, start the logging, and initialize the db
# connection prior to any other imports, since some of the imports will invoke
# setup methods
logs.start_logging()
db_connection.initialize()

from pulp.server.agent.direct.services import Services as AgentServices
from pulp.server.auth.admin import ensure_admin
from pulp.server.auth.authorization import ensure_builtin_roles
from pulp.plugins.loader import api as plugin_api
from pulp.server.db.version import check_version
from pulp.server.debugging import StacktraceDumper
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.managers import factory as manager_factory
from pulp.server.webservices.controllers import (
    agent, consumer_groups, consumers, contents, dispatch, events, plugins, 
    repo_groups, repositories, root_actions, users)
from pulp.server.webservices.middleware.exception import ExceptionHandlerMiddleware
from pulp.server.webservices.middleware.postponed import PostponedOperationMiddleware

# constants and application globals --------------------------------------------

URLS = (
    # Please keep the following in alphabetical order.
    '/v2/actions', root_actions.application,
    '/v2/agent', agent.application,
    '/v2/consumer_groups', consumer_groups.application,
    '/v2/consumers', consumers.application,
    '/v2/content', contents.application,
    '/v2/events', events.application,
    '/v2/plugins', plugins.application,
    '/v2/queued_calls', dispatch.queued_call_application,
    '/v2/repo_groups', repo_groups.application,
    '/v2/repositories', repositories.application,
    '/v2/task_groups', dispatch.task_group_application,
    '/v2/tasks', dispatch.task_application,
    '/v2/users', users.application,
    )

_LOG = logging.getLogger(__name__)
_IS_INITIALIZED = False

STACK_TRACER = None

# initialization ---------------------------------------------------------------

def _initialize_pulp():
    # XXX ORDERING COUNTS
    # This initialization order is very sensitive, and each touches a number of
    # sub-systems in pulp. If you get this wrong, you will have pulp tripping
    # over itself on start up. If you do not know where to add something, ASK!
    global _IS_INITIALIZED, STACK_TRACER
    if _IS_INITIALIZED:
        return
    _IS_INITIALIZED = True

    # check our db version and other support
    check_version()

    # pulp generic content initialization
    manager_factory.initialize()
    plugin_api.initialize()

    # new async dispatch initialization
    dispatch_factory.initialize()

    # ensure necessary infrastructure
    ensure_builtin_roles()
    ensure_admin()

    # agent services
    AgentServices.start()

    # setup debugging, if configured
    if config.config.getboolean('server', 'debugging_mode'):
        STACK_TRACER = StacktraceDumper()
        STACK_TRACER.start()



def wsgi_application():
    """
    Application factory to create, configure, and return a WSGI application
    using the web.py framework and custom Pulp middleware.
    @return: wsgi application callable
    """
    application = web.subdir_application(URLS).wsgifunc()
    stack_components = [application, PostponedOperationMiddleware, ExceptionHandlerMiddleware]
    stack = reduce(lambda a, m: m(a), stack_components)
    _initialize_pulp()
    return stack
