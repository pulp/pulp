# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
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

import web

from pulp.server.api.package import PackageApi
from pulp.server.api.file import FileApi
from pulp.server.auth.authorization import READ
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import (
    auth_required, error_handler)


papi = PackageApi()
fapi = FileApi()

class Packages(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self):
        """
        List orphaned packages.
        @return: a list of packages
        """
        return self.ok(papi.orphaned_packages())

class Files(JSONController):

    @error_handler
    @auth_required(READ)
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
