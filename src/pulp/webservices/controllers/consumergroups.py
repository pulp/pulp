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

from pulp.api.consumer_group import ConsumerGroupApi
from pulp.webservices.controllers.base import JSONController
from pulp.webservices.role_check import RoleCheck

# consumers api ---------------------------------------------------------------

api = ConsumerGroupApi()

# controllers -----------------------------------------------------------------

class ConsumerGroups(JSONController):

    @JSONController.error_handler
    @RoleCheck()
    def GET(self):
        """
        List all available consumergroups.
        @return: a list of all consumergroups
        """
        # implement filters
        return self.ok(api.consumergroups())

    @JSONController.error_handler
    @RoleCheck()
    def PUT(self):
        """
        Create a new consumer group.
        @return: consumer group metadata on successful creation
        """
        consumergroup_data = self.params()
        consumergroup = api.create(consumergroup_data['id'], consumergroup_data['description'],
                                   consumergroup_data['consumerids'])
        return self.created(consumergroup['id'], consumergroup)

    @JSONController.error_handler
    @RoleCheck()
    def DELETE(self):
        """
        @return: True on successful deletion of all consumer groups
        """
        api.clean()
        return self.ok(True)


class ConsumerGroup(JSONController):

    @JSONController.error_handler
    @RoleCheck()
    def GET(self, id):
        """
        Get a consumergroup's meta data.
        @param id: consumer group id
        @return: consumer group meta data
        """
        return self.ok(api.consumergroup(id))

    @JSONController.error_handler
    @RoleCheck()
    def PUT(self, id):
        """
        Update consumer group
        @param id: The consumer group id
        """
        consumergroup = self.params()
        consumergroup = api.update(consumergroup)
        return self.ok(True)

    @JSONController.error_handler
    @RoleCheck()
    def DELETE(self, id):
        """
        Delete a consumer group.
        @param id: consumer group id
        @return: True on successful deletion of consumer
        """
        api.delete(id=id)
        return self.ok(True)

class ConsumerGroupActions(JSONController):

    # See pulp.webservices.repositories.RepositoryActions for design

    exposed_actions = (
        'bind',
        'unbind',
        'add_consumer',
        'delete_consumer',
        'installpackages',
    )

    def bind(self, id):
        """
        Bind (subscribe) all the consumers in a consumergroup to a repository.
        @param id: consumer group id
        """
        data = self.params()
        api.bind(id, data)
        return self.ok(True)

    def unbind(self, id):
        """
        Unbind (unsubscribe) all the consumers in a consumergroup from a repository.
        @param id: consumer group id
        """
        data = self.params()
        api.unbind(id, data)
        return self.ok(None)


    def add_consumer(self, id):
        """
        Add a consumer to the group.
        @param id: consumer group id
        """
        data = self.params()
        api.add_consumer(id, data)
        return self.ok(True)

    def delete_consumer(self, id):
        """
        Delete a consumer from the group.
        @param id: consumer group id
        """
        data = self.params()
        api.delete_consumer(id, data)
        return self.ok(None)
    
    
    def installpackages(self, id):
        """
        Install packages.
        Body contains a list of package names.
        """
        data = self.params()
        names = data.get('packagenames', [])
        return self.ok(api.installpackages(id, names))

    @JSONController.error_handler
    @RoleCheck()
    def POST(self, id, action_name):
        """
        Consumer action dispatcher
        @type id: str
        @param id: controller id
        @type action_name: str
        @param action_name: action name
        """
        action = getattr(self, action_name, None)
        if action is None:
            return self.internal_server_error('No implementation for %s found' % action_name)
        return action(id)


# web.py application ----------------------------------------------------------

URLS = (
    '/$', 'ConsumerGroups',
    '/([^/]+)/$', 'ConsumerGroup',
    '/([^/]+)/(%s)/$' % '|'.join(ConsumerGroupActions.exposed_actions),
    'ConsumerGroupActions',
)

application = web.application(URLS, globals())
