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

# packages api ----------------------------------------------------------------

API = PackageApi(CONFIG)

# packages controllers --------------------------------------------------------

class Packages(JSONController):
    
    @JSONController.error_handler
    def GET(self):
        """
        List available packages.
        @return: a list of packages
        """
        return self.ok(API.package_descriptions())
    
    @JSONController.error_handler
    def DELETE(self):
        """
        Delete all packages.
        @return: True on success
        """
        API.clean()
        return self.ok(True)

    @JSONController.error_handler
    def PUT(self):
        """
        Create a new package.
        @return: package meta data on successful creation of package
        """
        data = self.params()
        package = API.create(data['name'], data['epoch'],data['version'],  
                             data['release'], data['arch'], data['description'],
                             data['checksum_type'], data['checksum'], data['filename'])
        return self.created(None, package)
    
    
class Package(JSONController):
    
    @JSONController.error_handler
    def GET(self, id):
        """
        Get information on a sinble package.
        @param id: package id
        @return: package meta data corresponding to id
        """
        return self.ok(API.package(id))

    @JSONController.error_handler
    def DELETE(self, id):
        '''
        @param id: package id
        '''
        API.delete(id)
        return self.ok(True)
    
    
class PackageActions(JSONController):
    
    # See juicer.repositories.RepositoryActions for design
    
    exposed_actions = (
    )
    
    @JSONController.error_handler
    def POST(self, id, action_name):
        action = getattr(self, action_name, None)
        if action is None:
            self.internal_server_error('No implementation for %s found' % action_name)
        return action(id)
    

class Versions(JSONController):

    @JSONController.error_handler
    def GET(self, name, version, release, epoch, arch):
        pv = API.package_by_ivera(name, version, epoch, release, arch)
        return self.ok(pv)

# web.py application ----------------------------------------------------------

URLS = (
    '/$', 'Packages',
    '/([^/]+)/$', 'Package',
    #'/([^/]+)/(%s)/$' % '|'.join(PackageActions.exposed_actions), 'Package',
    '/([^/]+)/([^/]+)/([^/]+)/([^/]+)/([^/]+)/', 'Versions',
)

application = web.application(URLS, globals())