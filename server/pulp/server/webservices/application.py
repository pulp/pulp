# Copyright (c) 2010-2012 Red Hat, Inc.
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


def _handle_with_processors(self):
    """
    This keeps the web.py wsgi app from trying to handle otherwise unhandled
    exceptions and lets Pulp error handling middleware handle them instead
    This exists here as it is the first place that Pulp imports web.py, so all
    web.py applications will be instantiated *after* their base class is patched
    """
    def process(processors):
        if processors:
            p, processors = processors[0], processors[1:]
            return p(lambda: process(processors))
        else:
            return self.handle()
    return process(self.processors)


import web

web.application.handle_with_processors = _handle_with_processors

from pulp.server import config  # automatically loads config
from pulp.server import logs

# We need to read the config, start the logging, and initialize the db
# connection prior to any other imports, since some of the imports will invoke
# setup methods.
logs.start_logging()
from pulp.server import initialization

from pulp.server.agent.direct.services import Services as AgentServices
from pulp.server.debugging import StacktraceDumper
from pulp.server.db.migrate import models as migration_models
from pulp.server.webservices.controllers import (
    agent, consumer_groups, consumers, contents, dispatch, events, permissions,
    plugins, repo_groups, repositories, roles, root_actions, status, users)
from pulp.server.webservices.middleware.exception import ExceptionHandlerMiddleware
from pulp.server.webservices.middleware.postponed import PostponedOperationMiddleware
from pulp.server.webservices.middleware.framework_router import FrameworkRoutingMiddleware
from pulp.server.webservices.wsgi import application as django_application

# constants and application globals --------------------------------------------

URLS = (
    # Please keep the following in alphabetical order.
    '/v2/actions', root_actions.application,
    '/v2/agent', agent.application,
    '/v2/consumer_groups', consumer_groups.application,
    '/v2/consumers', consumers.application,
    '/v2/content', contents.application,
    '/v2/events', events.application,
    '/v2/permissions', permissions.application,
    '/v2/plugins', plugins.application,
    '/v2/repo_groups', repo_groups.application,
    '/v2/repositories', repositories.application,
    '/v2/roles', roles.application,
    '/v2/status', status.application,
    '/v2/tasks', dispatch.task_application,
    '/v2/users', users.application,
)

logger = logging.getLogger(__name__)
_IS_INITIALIZED = False

STACK_TRACER = None


def _initialize_pulp():

    # This initialization order is very sensitive, and each touches a number of
    # sub-systems in pulp. If you get this wrong, you will have pulp tripping
    # over itself on start up.

    global _IS_INITIALIZED, STACK_TRACER
    if _IS_INITIALIZED:
        return

    # Even though this import does not get used anywhere, we must import it for the Celery
    # application to be initialized. Also, this import cannot happen in the usual PEP-8 location,
    # as it calls initialization code at the module level. Calling that code at the module level
    # is necessary for the Celery application to initialize.
    from pulp.server.async import app

    # configure agent services
    AgentServices.init()

    # Verify the database has been migrated to the correct version. This is
    # very likely a reason the server will fail to start.
    try:
        migration_models.check_package_versions()
    except Exception:
        msg = 'The database has not been migrated to the current version. '
        msg += 'Run pulp-manage-db and restart the application.'
        raise initialization.InitializationException(msg), None, sys.exc_info()[2]

    # There's a significantly smaller chance the following calls will fail.
    # The previous two are likely user errors, but the remainder represent
    # something gone horribly wrong. As such, I'm not going to account for each
    # and instead simply let the exception itself bubble up.

    # start agent services
    AgentServices.start()

    # Setup debugging, if configured
    if config.config.getboolean('server', 'debugging_mode'):
        STACK_TRACER = StacktraceDumper()
        STACK_TRACER.start()

    # If we got this far, it was successful, so flip the flag
    _IS_INITIALIZED = True

def wsgi_application():
    """
    Application factory to create, configure, and return a WSGI application
    using the web.py framework and custom Pulp middleware.
    @return: wsgi application callable
    """
    webpy_application = web.subdir_application(URLS).wsgifunc()
    webpy_stack_components = [webpy_application, PostponedOperationMiddleware, ExceptionHandlerMiddleware]
    webpy_stack = reduce(lambda a, m: m(a), webpy_stack_components)

    app = FrameworkRoutingMiddleware(webpy_stack, django_application)

    # The following intentionally don't raise the exception. The logging writes
    # to both error_log and pulp.log. Raising the exception caused it to be
    # logged twice to error_log, which was annoying. The Pulp server still
    # fails to start (I can't even log in), and on attempts to use it the
    # initialize failure message is logged again. I like that behavior so I
    # think this approach makes sense. But if there is a compelling reason to
    # raise the exception, change it; I don't have a strong conviction behind
    # this approach other than the duplicate logging and the appearance that it
    # works as desired.
    # jdob, Nov 21, 2012

    try:
        _initialize_pulp()
    except initialization.InitializationException, e:
        logger.fatal('*************************************************************')
        logger.fatal('The Pulp server failed to start due to the following reasons:')
        logger.exception('  ' + e.message)
        logger.fatal('*************************************************************')
        return
    except:
        logger.fatal('*************************************************************')
        logger.exception('The Pulp server encountered an unexpected failure during initialization')
        logger.fatal('*************************************************************')
        return

    logger.info('*************************************************************')
    logger.info('The Pulp server has been successfully initialized')
    logger.info('*************************************************************')

    return app
