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

# web.py application ----------------------------------------------------------

URLS = (
    '/$', 'Root',
    '/bulk/$', 'Bulk',
    '/([^/]+)/$', 'Consumer',
    '/([^/]+)/bind/$', 'Bind',
    '/([^/]+)/unbind/$', 'Unbind',
    '/([^/]+)/profile/$', 'Profile',
)

application = web.application(URLS, globals())

# consumers api ---------------------------------------------------------------

API = ConsumerApi(CONFIG)

# controllers -----------------------------------------------------------------
    
class Root(JSONController):

    @JSONController.error_handler
    def GET(self):
        """
        List all available consumers.
        @return: a list of all consumers
        """
        params = self.params()
        if len(params) == 1:
            pkgname = params.get('name')
            if pkgname:
                result = API.consumers_with_package_name(pkgname)
                return self.output(result)
            else:
                return self.output([])
        return self.output(API.consumers())
     
    @JSONController.error_handler
    def POST(self):
        """
        Create a new consumer.
        @return: consumer meta data on successful creation of consumer
        """
        consumer_data = self.input()
        consumer = API.create(consumer_data['id'], consumer_data['description'])
        return self.output(consumer)

    @JSONController.error_handler
    def DELETE(self):
        """
        @return: True on successful deletion of all consumers
        """
        API.clean()
        return self.output(None)

 
class Consumer(JSONController):

    @JSONController.error_handler
    def GET(self, id):
        """
        Get a consumer's meta data.
        @param id: consumer id
        @return: consumer meta data
        """
        return self.output(API.consumer(id))
    
    @JSONController.error_handler
    def POST(self, id):
        """
        Update
        @param id: The consumer id
        @type id: str
        """
        consumer = self.input()
        consumer = API.update(consumer)
        return self.output(None)

    @JSONController.error_handler
    def DELETE(self, id):
        """
        Delete a consumer.
        @param id: consumer id
        @return: True on successful deletion of consumer
        """
        API.delete(id=id)
        return self.output(None)


class Bulk(JSONController):

    @JSONController.error_handler
    def POST(self):
        API.bulkcreate(self.input())
        return self.output(None)


class Bind(JSONController):
    
    @JSONController.error_handler
    def POST(self, id):
        """
        Bind (subscribe) a user to a repository.
        @param id: consumer id
        @return: True on successful bind
        """
        data = self.input()
        API.bind(id, data)
        return self.output(True)


class Unbind(JSONController):
    
    @JSONController.error_handler
    def POST(self, id):
        """
        Unbind (unsubscribe) a user to a repository.
        @param id: consumer id
        @return: True on successful unbind
        """
        data = self.input()
        API.unbind(id, data)
        return self.output(True)


class Profile(JSONController):
    """
    update/add Consumer profile information. eg:package, hardware etc
    """
    @JSONController.error_handler
    def POST(self, id):
        API.profile_update(id, self.input())
        return self.output(None)
