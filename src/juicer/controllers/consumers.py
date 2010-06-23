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
from pulp.api.consumer import ConsumerApi

# consumers api ---------------------------------------------------------------

API = ConsumerApi(CONFIG)

# controllers -----------------------------------------------------------------
    
class Consumers(JSONController):

    @JSONController.error_handler
    def GET(self):
        """
        List all available consumers.
        @return: a list of all consumers
        """
        filters = self.filters()
        if len(filters) == 1:
            pkgname = filters.get('name')
            if pkgname:
                result = API.consumers_with_package_name(pkgname)
                return self.ok(result)
            else:
                return self.ok([])
        return self.ok(API.consumers())
     
    @JSONController.error_handler
    def PUT(self):
        """
        Create a new consumer.
        @return: consumer meta data on successful creation of consumer
        """
        consumer_data = self.params()
        consumer = API.create(consumer_data['id'], consumer_data['description'])
        return self.created(consumer['id'], consumer)

    @JSONController.error_handler
    def DELETE(self):
        """
        @return: True on successful deletion of all consumers
        """
        API.clean()
        return self.ok(True)

 
class Consumer(JSONController):

    @JSONController.error_handler
    def GET(self, id):
        """
        Get a consumer's meta data.
        @param id: consumer id
        @return: consumer meta data
        """
        return self.ok(API.consumer(id))
    
    @JSONController.error_handler
    def PUT(self, id):
        """
        Update consumer
        @param id: The consumer id
        @type id: str
        """
        consumer = self.params()
        consumer = API.update(consumer)
        return self.ok(True)

    @JSONController.error_handler
    def DELETE(self, id):
        """
        Delete a consumer.
        @param id: consumer id
        @return: True on successful deletion of consumer
        """
        API.delete(id=id)
        return self.ok(True)


class Bulk(JSONController):
    # XXX this class breaks the restful practices.... (need a better solution)
    @JSONController.error_handler
    def POST(self):
        API.bulkcreate(self.params())
        return self.ok(True)


class ConsumerActions(JSONController):
    
    # See juicer.repositories.RepositoryActions for design
    
    exposed_actions = (
        'bind',
        'unbind',
        'profile',
        'installpackages',
        'packages',
    )
    
    def bind(self, id):
        """
        Bind (subscribe) a user to a repository.
        @param id: consumer id
        """
        data = self.params()
        API.bind(id, data)
        return self.ok(True)

    def unbind(self, id):
        """
        Unbind (unsubscribe) a user to a repository.
        @param id: consumer id
        """
        data = self.params()
        API.unbind(id, data)
        return self.ok(None)
    
    def profile(self, id):
        """
        update/add Consumer profile information. eg:package, hardware etc
        """
        API.profile_update(id, self.params())
        return self.ok(True)

    def installpackages(self, id):
        """
        Install packages.
        Body contains a list of package names.
        """
        data = self.input()
        names = data.get('packagenames', [])
        return self.ok(API.installpackages(id, names))
    
    def packages(self, id):
        """
        Get a consumer's set of packages
        @param id: consumer id
        @return: consumer's installed packages
        """
        return self.ok(API.packages(id))
    
    @JSONController.error_handler
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
    '/$', 'Consumers',
    '/bulk/$', 'Bulk',
    '/([^/]+)/$', 'Consumer',
    '/([^/]+)/(%s)/$' % '|'.join(ConsumerActions.exposed_actions), 'ConsumerActions',
)

application = web.application(URLS, globals())
