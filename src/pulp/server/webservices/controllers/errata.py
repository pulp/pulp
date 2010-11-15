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

from pulp.server.api.errata import ErrataApi
from pulp.server.webservices import http
from pulp.server.webservices import mongo
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.role_check import RoleCheck

# globals ---------------------------------------------------------------------

api = ErrataApi()
log = logging.getLogger('pulp')

class Errata(JSONController):

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def GET(self):
        """
        List all available errata.
        @return: a list of all users
        """
        # implement filters
        return self.ok(api.errata())

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def PUT(self):
        """
        Create a new errata
        @return: errata that was created
        """
        errata_data = self.params()
        errata = api.create(errata_data['id'],
                          errata_data['title'],
                          errata_data['description'],
                          errata_data['version'],
                          errata_data['release'],
                          errata_data['type'],
                          errata_data.get('status', ""),
                          errata_data.get('updated', ""),
                          errata_data.get('issued', ""),
                          errata_data.get('pushcount', ""),
                          errata_data.get('from_str', ""),
                          errata_data.get('reboot_suggested', ""),
                          errata_data.get('references', []),
                          errata_data.get('pkglist', []),
                          errata_data.get('repo_defined', False),
                          errata_data.get('immutable', False))
        return self.created(errata['id'], errata)

    def POST(self):
        # REST dictates POST to collection, and PUT to specific resource for
        # creation, this is the start of supporting both
        return self.PUT()


class Erratum(JSONController):

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def GET(self, id):
        """
        Get a erratum information
        @param id: erratum id
        @return: erratum metadata
        """
        return self.ok(api.erratum(id))

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def PUT(self, id):
        """
        Update errata
        @param id: The erratum id
        """
        erratum = self.params()
        erratum = api.update(erratum)
        return self.ok(True)

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def DELETE(self, id):
        """
        Delete an errata
        @param id: errata id to delete
        @return: True on successful deletion of erratum
        """
        api.delete(id=id)
        return self.ok(True)
# web.py application ----------------------------------------------------------

URLS = (
    '/$', 'Errata',
    '/([^/]+)/$', 'Erratum',
)

application = web.application(URLS, globals())
