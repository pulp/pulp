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

from pulp.server.api.package import PackageApi
from pulp.server.api.file import FileApi
from pulp.server.auth.authorization import READ
from pulp.server.webservices.controllers.base import JSONController

papi = PackageApi()
fapi = FileApi()

class Packages(JSONController):
    
    @JSONController.error_handler
    @JSONController.auth_required(READ)
    def GET(self):
        """
        List orphaned packages.
        @return: a list of packages
        """
        return self.ok(papi.orphaned_packages())
    
class Files(JSONController):
    
    @JSONController.error_handler
    @JSONController.auth_required(READ)
    def GET(self):
        """
        List orphaned packages.
        @return: a list of packages
        """
        return self.ok(fapi.orphaned_files())
    
# web.py application ----------------------------------------------------------

URLS = (
    '/packages/$', 'Packages',
    '/files/$', 'Files',
)

application = web.application(URLS, globals())