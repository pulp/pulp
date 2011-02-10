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
from pulp.server.api.repo import RepoApi
from pulp.server.auth.authorization import (CREATE, READ, UPDATE, DELETE,
    EXECUTE, grant_automatic_permissions_for_created_resource)
from pulp.server.webservices import http
from pulp.server.webservices.controllers.base import (JSONController,
    AsyncController)

# globals ---------------------------------------------------------------------

api = ErrataApi()
rapi = RepoApi()
log = logging.getLogger('pulp')

class Errata(JSONController):

    @JSONController.error_handler
    @JSONController.auth_required(READ)
    def GET(self):
        """
        List all available errata.
        @return: a list of all users
        """
        # implement filters
        return self.ok(api.errata())

    @JSONController.error_handler
    @JSONController.auth_required(CREATE)
    def POST(self):
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
        resource = http.resource_path(http.extend_uri_path(errata['id']))
        grant_automatic_permissions_for_created_resource(resource)
        return self.created(errata['id'], errata)

    def PUT(self):
        log.debug('deprecated Errata.PUT method called')
        return self.POST()


class Erratum(JSONController):

    @JSONController.error_handler
    @JSONController.auth_required(READ)
    def GET(self, id):
        """
        Get a erratum information
        @param id: erratum id
        @return: erratum metadata
        """
        return self.ok(api.erratum(id))

    @JSONController.error_handler
    @JSONController.auth_required(UPDATE)
    def PUT(self, id):
        """
        Update errata
        @param erratum obj: The erratum object
        """
        erratum = self.params()
        erratum = api.update(erratum)
        return self.ok(True)

    @JSONController.error_handler
    @JSONController.auth_required(DELETE)
    def DELETE(self, id):
        """
        Delete an errata
        @param id: errata id to delete
        @return: True on successful deletion of erratum
        """
        api.delete(id=id)
        return self.ok(True)

class ErrataActions(AsyncController):

    # All actions have been gathered here into one controller class for both
    # convenience and automatically generate the regular expression that will
    # map valid actions to this class. This also provides a single point for
    # querying existing tasks.
    #
    # There are two steps to implementing a new action:
    # 1. The action name must be added to the tuple of exposed_actions
    # 2. You must add a method to this class with the same name as the action
    #    that takes two positional arguments: 'self' and 'id' where id is the
    #    the repository id. Additional parameters from the body can be
    #    fetched and de-serialized via the self.params() call.

    # NOTE the intersection of exposed_actions and exposed_fields must be empty
    exposed_actions = (
        'get_repos',
    )

    def get_repos(self, id):
        """
         Return repoids with available errata
         @param id: errata id
         @return List of repoids which have specified errata id
        """
        return self.ok(rapi.find_repos_by_errataid(id))

    @JSONController.error_handler
    @JSONController.auth_required(EXECUTE)
    def POST(self, id, action_name):
        """
        Action dispatcher. This method checks to see if the action is exposed,
        and if so, implemented. It then calls the corresponding method (named
        the same as the action) to handle the request.
        @type id: str
        @param id: errata id
        @type action_name: str
        @param action_name: name of the action
        @return: http response
        """
        errata = api.errata(id)
        if not errata:
            return self.not_found('No errata with id %s found' % id)
        action = getattr(self, action_name, None)
        if action is None:
            return self.internal_server_error('No implementation for %s found' % action_name)
        return action(id)
# web.py application ----------------------------------------------------------

URLS = (
    '/$', 'Errata',
    '/([^/]+)/$', 'Erratum',
    '/([^/]+)/(%s)/$' % '|'.join(ErrataActions.exposed_actions), 'ErrataActions',
)

application = web.application(URLS, globals())
