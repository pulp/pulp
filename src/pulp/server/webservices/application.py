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
from pulp.server.webservices.controllers.consumers import repo_api

connection.initialize()

from pulp.server.api import consumer_history
from pulp.server.api import scheduled_sync
from pulp.server.api import repo
from pulp.server.db.version import check_version
from pulp.server.debugging import StacktraceDumper
from pulp.server.logs import start_logging
from pulp.server.webservices.controllers import (
    audit, cds, consumergroups, consumers, content, distribution, errata,
    filters, orphaned, packages, permissions, repositories, roles, services,
    users)


urls = (# alphabetical order, please
    '/cds', cds.application,
    '/consumergroups', consumergroups.application,
    '/consumers', consumers.application,
    '/content', content.application,
    '/distribution', distribution.application,
    '/errata', errata.application,
    '/events', audit.application,
    '/filters', filters.application,
    '/orphaned', orphaned.application,
    '/packages', packages.application,
    '/permissions', permissions.application,
    '/repositories', repositories.application,
    '/roles', roles.application,
    '/services', services.application,
    '/users', users.application,
)

_stacktrace_dumper = None


def _initialize_pulp():
    global _stacktrace_dumper
    # pulp initialization methods
    start_logging()
    check_version()
    ensure_builtin_roles()
    ensure_admin()
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
    repo.clear_all_sync_in_progress()
    scheduled_sync.init_scheduled_syncs()



def wsgi_application():
    """
    Application factory to create, configure, and return a WSGI application
    using the web.py framework.
    @return: wsgi application callable
    """
    application = web.subdir_application(urls)
    _initialize_pulp()
    return application.wsgifunc()
