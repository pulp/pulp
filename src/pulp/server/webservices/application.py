# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import atexit
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
#connection prior to any other imports, since some of the imports will invoke
# setup methods
logs.start_logging()
db_connection.initialize()

from pulp.repo_auth.repo_cert_utils import M2CRYPTO_HAS_CRL_SUPPORT
from pulp.server import async
from pulp.server import auditing
from pulp.server.gc_agent.direct.services import Services as AgentServices
from pulp.server.api import consumer_history
from pulp.server.api import scheduled_sync
from pulp.server.api import repo
from pulp.server.auth.admin import ensure_admin
from pulp.server.auth.authorization import ensure_builtin_roles
from pulp.server.content import loader as plugin_loader
from pulp.server.db.version import check_version
from pulp.server.debugging import StacktraceDumper
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.event.dispatcher import EventDispatcher
from pulp.server.managers import factory as manager_factory
from pulp.server.webservices.controllers import (
    audit, cds, consumergroups, consumers, content, distribution, errata,
    filters, histories, jobs, orphaned, packages, permissions, statuses,
    repositories, roles, services, tasks, users, agent,)
from pulp.server.webservices.controllers import (
    dispatch, gc_contents, gc_plugins, gc_repositories, gc_consumers, gc_root_actions)
from pulp.server.webservices.middleware.exception import ExceptionHandlerMiddleware
from pulp.server.webservices.middleware.postponed import PostponedOperationMiddleware

# conatants and application globals --------------------------------------------

URLS = (
    # alphabetical order, please
    # default version (currently 1) api
    '/cds', cds.application,
    '/consumergroups', consumergroups.application,
    '/consumers', consumers.application,
    '/content', content.application,
    '/distributions', distribution.application,
    '/errata', errata.application,
    '/events', audit.application,
    '/filters', filters.application,
    '/histories', histories.application,
    '/jobs', jobs.application,
    '/orphaned', orphaned.application,
    '/packages', packages.application,
    '/permissions', permissions.application,
    '/repositories', repositories.application,
    '/statuses', statuses.application,
    '/roles', roles.application,
    '/services', services.application,
    '/tasks', tasks.application,
    '/users', users.application,
    # version 1 api
    '/v1/cds', cds.application,
    '/v1/consumergroups', consumergroups.application,
    '/v1/consumers', consumers.application,
    '/v1/content', content.application,
    '/v1/distributions', distribution.application,
    '/v1/errata', errata.application,
    '/v1/events', audit.application,
    '/v1/filters', filters.application,
    '/v1/histories', histories.application,
    '/v1/jobs', jobs.application,
    '/v1/orphaned', orphaned.application,
    '/v1/packages', packages.application,
    '/v1/permissions', permissions.application,
    '/v1/repositories', repositories.application,
    '/v1/repo_sync_status', statuses.application,
    '/v1/roles', roles.application,
    '/v1/services', services.application,
    '/v1/statuses', statuses.application,
    '/v1/tasks', tasks.application,
    '/v1/users', users.application,
    # version 2 api
    '/v2/actions', gc_root_actions.application,
    '/v2/agent', agent.application,
    '/v2/consumers', gc_consumers.application,
    '/v2/content', gc_contents.application,
    '/v2/jobs', dispatch.job_application,
    '/v2/plugins', gc_plugins.application,
    '/v2/queued_calls', dispatch.queued_call_application,
    '/v2/repositories', gc_repositories.application,
    '/v2/tasks', dispatch.task_application,
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
    if not M2CRYPTO_HAS_CRL_SUPPORT:
        _LOG.warning("M2Crypto lacks needed CRL functionality, therefore CRL checking will be disabled.")
    # ensure necessary infrastructure
    ensure_builtin_roles()
    ensure_admin()
    # clean up previous runs, if needed
    repo.clear_sync_in_progress_flags()
    # agent services
    AgentServices.start()
    # async subsystem and schedules tasks
    async.initialize()
    # pulp finalization methods, registered via 'atexit'
    atexit.register(async.finalize)
    # setup debugging, if configured
    if config.config.getboolean('server', 'debugging_mode'):
        STACK_TRACER = StacktraceDumper()
        STACK_TRACER.start()
    # setup recurring tasks
    auditing.init_culling_task()
    consumer_history.init_culling_task()
    scheduled_sync.init_scheduled_syncs()
    # pulp generic content initialization
    manager_factory.initialize()
    plugin_loader.initialize()
    # new async dispatch initialization
    dispatch_factory.initialize()


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
