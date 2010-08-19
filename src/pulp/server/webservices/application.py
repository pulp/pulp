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

from pulp.server.config import config
from pulp.server.logs import start_logging
from pulp.server.webservices import controllers


# NOTE: If you add a item here make sure you also add 
#       it to controllers/__init__.py
URLS = (
    '/test', controllers.test.application,
    '/consumers', controllers.consumers.application,
    '/consumergroups', controllers.consumergroups.application,
    '/events', controllers.audit.application,
    '/packages', controllers.packages.application,
    '/repositories', controllers.repositories.application,
    '/users', controllers.users.application,    
    '/errata', controllers.errata.application,
)


def _configure_application(application, config):
    pass


def wsgi_application():
    """
    Application factory to create, configure, and return a WSGI application
    using the web.py framework.
    
    @return: wsgi application callable
    """
    application = web.subdir_application(URLS)
    _configure_application(application, config)
    start_logging()
    return application.wsgifunc()
