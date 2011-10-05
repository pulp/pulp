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

import web

from pulp.server import async
from pulp.server import auditing
from pulp.server import config
from pulp.server.auth.admin import ensure_admin
from pulp.server.auth.authorization import ensure_builtin_roles
from pulp.server.db import connection

# We need to initialize the db connection and auditing prior to any other
# imports, since some of the imports will invoke setup methods
connection.initialize()

from pulp.server.api import consumer_history
from pulp.server.api import scheduled_sync
from pulp.server.api import repo
from pulp.server.db.version import check_version
from pulp.server.debugging import StacktraceDumper
from pulp.server.logs import start_logging
from pulp.server.webservices.controllers import (
    audit, cds, consumergroups, consumers, content, distribution, errata,
    filters, jobs, orphaned, packages, permissions, repositories, roles,
    services, tasks, users)
from pulp.server.webservices.controllers import (
    gc_contents, gc_plugins, gc_repositories)
from pulp.server.webservices.middleware.error import ErrorHandlerMiddleware


urls = (
    # alphabetical order, please
    # default version (currently 1) api
    '/cds', cds.application,
    '/consumergroups', consumergroups.application,
    '/consumers', consumers.application,
    '/content', content.application,
    '/distribution', distribution.application,
    '/errata', errata.application,
    '/events', audit.application,
    '/filters', filters.application,
    '/jobs', jobs.application,
    '/orphaned', orphaned.application,
    '/packages', packages.application,
    '/permissions', permissions.application,
    '/repositories', repositories.application,
    '/roles', roles.application,
    '/services', services.application,
    '/tasks', tasks.application,
    '/users', users.application,
    # version 1 api
    '/v1/cds', cds.application,
    '/v1/consumergroups', consumergroups.application,
    '/v1/consumers', consumers.application,
    '/v1/content', content.application,
    '/v1/distribution', distribution.application,
    '/v1/errata', errata.application,
    '/v1/events', audit.application,
    '/v1/filters', filters.application,
    '/v1/jobs', jobs.application,
    '/v1/orphaned', orphaned.application,
    '/v1/packages', packages.application,
    '/v1/permissions', permissions.application,
    '/v1/repositories', repositories.application,
    '/v1/roles', roles.application,
    '/v1/services', services.application,
    '/v1/tasks', tasks.application,
    '/v1/users', users.application,
    # version 2 api
    '/v2/content', gc_contents.application,
    '/v2/plugins', gc_plugins.application,
    '/v2/repositories', gc_repositories.application,
)

_stacktrace_dumper = None


def _initialize_pulp():
    # XXX ORDERING COUNTS
    # This initialization order is very sensitive, and each touches a number of
    # sub-systems in pulp. If you get this wrong, you will have pulp tripping
    # over itself on start up. If you do not know where to add something, ASK!
    global _stacktrace_dumper
    # start logging and verify we can run
    start_logging()
    check_version()
    # ensure necessary infrastructure
    ensure_builtin_roles()
    ensure_admin()
    # clean up previous runs, if needed
    repo.clear_sync_in_progress_flags()
    # initialize current run
    async.initialize()
    # pulp finalization methods, registered via 'atexit'
    atexit.register(async.finalize)
    # setup debugging, if configured
    if config.config.getboolean('server', 'debugging_mode') and \
            _stacktrace_dumper is None:
        _stacktrace_dumper = StacktraceDumper()
        _stacktrace_dumper.start()
    # setup recurring tasks
    auditing.init_culling_task()
    consumer_history.init_culling_task()
    scheduled_sync.init_scheduled_syncs()



def wsgi_application():
    """
    Application factory to create, configure, and return a WSGI application
    using the web.py framework.
    @return: wsgi application callable
    """
    application = web.subdir_application(urls)
    # TODO make debug configurable
    stack = ErrorHandlerMiddleware(application.wsgifunc(), debug=True)
    _initialize_pulp()
    return stack