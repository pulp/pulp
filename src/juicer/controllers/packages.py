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

from juicer.controllers.base import JSONController
from juicer.runtime import CONFIG
from pulp.api.package import PackageApi

# web.py application ----------------------------------------------------------

# /packages/
# GET    -  List of all package names and descriptions
# POST   -  Create a new package
# DELETE -  Delete all packages
# 
# /packages/<name>
# GET    -  All packages for that package name
# DELETE -  All packages for that package name
# 
# /packages/<name>/<version>/<release>/<epoch>/<arch>
# GET    -  Package version details for that package version

URLS = (
    '/$', 'Root',
    '/([^/]+)/$', 'Packages',
    '/([^/]+)/([^/]+)/([^/]+)/([^/]+)/([^/]+)/', 'Versions',
)

application = web.application(URLS, globals())

# packages api ----------------------------------------------------------------

API = PackageApi(CONFIG)

# packages controllers --------------------------------------------------------

class Root(JSONController):
    
    @JSONController.error_handler
    def GET(self):
        """
        List available packages.
        @return: a list of packages
        """
        return self.output(API.package_descriptions())
    
    @JSONController.error_handler
    def POST(self):
        """
        Create a new package.
        @return: package meta data on successful creation of new package
        """
        pkg_data = self.input()
        pkg = API.create(pkg_data['id'], pkg_data['name'])
        return self.output(pkg)

    @JSONController.error_handler
    def DELETE(self):
        API.clean()
        return self.output(None)

    @JSONController.error_handler
    def POST(self):
        """
        @return: package meta data on successful creation of package
        """
        data = self.input()
        package = API.create(data['name'], data['epoch'],data['version'],  
                             data['release'], data['arch'], data['description'],
                             data['checksum_type'], data['checksum'], data['filename'])
        return self.output(package)
    
class Packages(JSONController):
    
    @JSONController.error_handler
    def GET(self, id):
        """
        Get information on a sinble package.
        @param id: package id
        @return: package meta data corresponding to id
        """
        return self.output(API.package(id))

    @JSONController.error_handler
    def DELETE(self, id):
        '''
        @param id: package id
        '''
        API.delete(packageid=id)
        return self.output(None)
    

class Versions(JSONController):

    @JSONController.error_handler
    def GET(self, name, version, release, epoch, arch):
        pv = API.package_by_ivera(name, version, epoch, release, arch)
        return self.output(pv)
