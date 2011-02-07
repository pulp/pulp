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
from pulp.server.auth.authorization import grant_auto_permissions_for_created_resource
from pulp.server.webservices import mongo
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.http import extend_uri_path, resource_path
from pulp.server.webservices.role_check import RoleCheck

# globals ---------------------------------------------------------------------

api = PackageApi()
log = logging.getLogger('pulp')

# packages controllers --------------------------------------------------------

class Packages(JSONController):

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def GET(self):
        """
        List available packages.
        @return: a list of packages
        """
        valid_filters = ('id', 'name')
        filters = self.filters(valid_filters)
        spec = mongo.filters_to_re_spec(filters)
        return self.ok(api.package_descriptions(spec))

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def DELETE(self):
        """
        Delete all packages.
        @return: True on success
        """
        api.clean()
        return self.ok(True)

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def PUT(self):
        """
        Create a new package.
        @return: package meta data on successful creation of package
        """
        data = self.params()
        package = api.create(data['name'], data['epoch'], data['version'],
                             data['release'], data['arch'], data['description'],
                             data['checksum_type'], data['checksum'], data['filename'])
        resource = resource_path(extend_uri_path(package['id']))
        grant_auto_permissions_for_created_resource(resource)
        return self.created(None, package)

    def POST(self):
        # REST dictates POST to collection, and PUT to specific resource for
        # creation, this is the start of supporting both
        return self.PUT()


class Package(JSONController):

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def GET(self, id):
        """
        Get information on a sinble package.
        @param id: package id
        @return: package meta data corresponding to id
        """
        return self.ok(api.package(id))

    @JSONController.error_handler
    def DELETE(self, id):
        '''
        @param id: package id
        '''
        api.delete(id)
        return self.ok(True)


class PackageDeferredFields(JSONController):

    # NOTE the intersection of exposed_fields and exposed_actions must be empty
    exposed_fields = (
    )

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def GET(self, id, field_name):
        field = getattr(self, field_name, None)
        if field is None:
            return self.internal_server_error('No implementation for %s found' % field_name)
        return field(id)


class PackageActions(JSONController):

    # See pulp.webservices.repositories.RepositoryActions for design

    # NOTE the intersection of exposed_actions and exposed_fields must be empty
    exposed_actions = (
    )

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def POST(self, id, action_name):
        action = getattr(self, action_name, None)
        if action is None:
            self.internal_server_error('No implementation for %s found' % action_name)
        return action(id)


class Versions(JSONController):

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def GET(self, name, version, release, epoch, arch):
        pv = api.package_by_ivera(name, version, epoch, release, arch)
        return self.ok(pv)

# web.py application ----------------------------------------------------------

URLS = (
    '/$', 'Packages',
    '/([^/]+)/$', 'Package',
    #'/([^/]+)/(%s)/$' % '|'.join(PackageDeferredFields.exposed_fields), 'PackageDeferredFields',
    '/([^/]+)/(%s)/$' % '|'.join(PackageActions.exposed_actions), 'PackageActions',
    '/([^/]+)/([^/]+)/([^/]+)/([^/]+)/([^/]+)/', 'Versions',
)

application = web.application(URLS, globals())
