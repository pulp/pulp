#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import web

from pulp.server import config # unused here, but initializes configuration
from pulp.server import auditing
from pulp.server.db import connection
# We need to initialize the db connection and auditing prior to any other 
# imports, since some of the imports will invoke setup methods
connection.initialize()
auditing.initialize()

from pulp.server.db.version import check_version
from pulp.server.logs import start_logging
from pulp.server.webservices.controllers import (
    audit, cds, consumergroups, consumers, errata, packages, 
    repositories, search, users, roles, distribution)


urls = (
    '/cds', cds.application,
    '/consumers', consumers.application,
    '/consumergroups', consumergroups.application,
    '/events', audit.application,
    '/packages', packages.application,
    '/repositories', repositories.application,
    '/search', search.application,
    '/users', users.application,
    '/errata', errata.application,
    '/roles', roles.application,
    '/distribution', distribution.application,
)


def wsgi_application():
    """
    Application factory to create, configure, and return a WSGI application
    using the web.py framework.
    @return: wsgi application callable
    """
    application = web.subdir_application(urls)
    start_logging()
    check_version()
    return application.wsgifunc()
