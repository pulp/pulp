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
import logging

import web

from pulp.server.webservices import mongo
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.role_check import RoleCheck
from pulp.server.api.package import PackageApi

papi = PackageApi()
log = logging.getLogger('pulp')

class DependencyActions(JSONController):


    @JSONController.error_handler
    @RoleCheck(admin=True)
    def PUT(self):
        """
        list of available dependencies required \
        for a specified package per repo.
        expects passed in pkgnames and repoids from POST data
        @return: a dict of printable dependency result and suggested packages
        """
        data = self.params()
        return self.ok(papi.package_dependency(data['pkgnames'], data['repoids']))
    
    def POST(self):
        # REST dictates POST to collection, and PUT to specific resource for
        # creation, this is the start of supporting both
        return self.PUT()
    
# web.py application ----------------------------------------------------------

URLS = (
    '/dependencies/$', 'DependencyActions',
)

application = web.application(URLS, globals())