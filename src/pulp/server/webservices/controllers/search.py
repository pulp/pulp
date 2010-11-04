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
from pulp.server.webservices import mongo
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.role_check import RoleCheck

# globals ---------------------------------------------------------------------

papi = PackageApi()
log = logging.getLogger('pulp')

# search controllers --------------------------------------------------------

class PackageSearch(JSONController):

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def GET(self):
        """
        List available packages.
        @return: a list of packages
        """
        log.error("search:   GET received")
        valid_filters = ('id', 'name')
        filters = self.filters(valid_filters)
        spec = mongo.filters_to_re_spec(filters)
        return self.ok(papi.package_descriptions(spec))


    @JSONController.error_handler
    @RoleCheck(admin=True)
    def PUT(self):
        """
        Search for matching packages 
        expects passed in regex search strings from POST data
        @return: package meta data on successful creation of package
        """
        data = self.params()
        name = None
        if data.has_key("name"):
            name = data["name"]
        epoch = None
        if data.has_key("epoch"):
            epoch = data["epoch"]
        version = None
        if data.has_key("version"):
            version = data["version"]
        release = None
        if data.has_key("release"):
            release = data["release"]
        arch = None
        if data.has_key("arch"):
            arch = data["arch"]
        filename = None
        if data.has_key("filename"):
            filename = data["filename"]
        return self.ok(papi.packages(name=name, epoch=epoch, version=version,
            release=release, arch=arch, filename=filename, regex=True))

    def POST(self):
        # REST dictates POST to collection, and PUT to specific resource for
        # creation, this is the start of supporting both
        return self.PUT()


# web.py application ----------------------------------------------------------

URLS = (
    #'/$', 'Search',
    '/packages/$', 'PackageSearch',
    #'/packages/([^/]+)/$', 'PackageSearch',
    #'/consumers/([^/]+)/$', 'ConsumerSearch',
    #'/repositories/([^/]+)/$', 'RepositorySearch',
    #'/errata/([^/]+)/$', 'ErrataSearch',
    #'/([^/]+)/(%s)/$' % '|'.join(PackageDeferredFields.exposed_fields), 'PackageDeferredFields',
    #'/([^/]+)/(%s)/$' % '|'.join(PackageActions.exposed_actions), 'PackageActions',
    #'/([^/]+)/([^/]+)/([^/]+)/([^/]+)/([^/]+)/', 'Versions',
)

application = web.application(URLS, globals())
