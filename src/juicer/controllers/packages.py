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

__author__ = 'Jason L Connor <jconnor@redhat.com>'

import web

from juicer.controllers.base import JSONController
from pulp.api.package import PackageApi
from pulp.util import loadConfig

# web.py application ----------------------------------------------------------

URLS = (
    '/$', 'Root',
    '/([^/]+)/$', 'Package',
)

application = web.application(URLS, globals())

# packages api ----------------------------------------------------------------

config = loadConfig('/etc/pulp.ini')
API = PackageApi(config)

# packages controllers --------------------------------------------------------

class Root(JSONController):
    
    def GET(self):
        """
        @return: a list of packages
        """
        return self.output(API.packages())
    
    def POST(self):
        """
        @return: package meta data on successful creation of new package
        """
        pkg_data = self.input()
        pkg = API.create(pkg_data['id'], pkg_data['name'])
        return self.output(pkg)
    

class Package(JSONController):
    
    def GET(self, id):
        """
        @param id: package id
        @return: package meta data corresponding to id
        """
        return self.output(API.package(id))