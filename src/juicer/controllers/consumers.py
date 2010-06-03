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
    '/([^/]+)/$', 'Consumer',
    '/(\d+)/bind/(\d+)', 'Bind',
    '/(\d+)/unbind/(\d+)', 'Unbind',
)

application = web.application(URLS, globals())

# consumers api ---------------------------------------------------------------

API = ConsumerApi(CONFIG)

# controllers -----------------------------------------------------------------
    
class Root(JSONController):

    def GET(self):
        """
        @return: a list of all consumers
        """
        return self.output(API.consumers())
     
    def POST(self):
        """
        @return: consumer meta data on successful creation of consumer
        """
        consumer_data = self.input()
        consumer = API.create(consumer_data['id'], consumer_data['description'])
        return self.output(consumer)
   
 
class Consumer(JSONController):

    def GET(self, id):
        """
        @param id: consumer id
        @return: consumer meta data
        """
        return self.output(API.consumer(id))

    def DELETE(self, id):
        """
        @param id: consumer id
        @return: True on successful deletion of consumer
        """
        API.delete(id)
        return self.output(True)


class Bind(object):
    """
    Bind (subscribe) a user to a repository.
    """
    def POST(self, id, repoid):
        API.bind(id, repoid)
        return self.output(True)


class Unbind(object):
    """
    Unbind (unsubscribe) a user to a repository.
    """
    def POST(self, id, repoid):
        API.unbind(id, repoid)
        return self.output(True)
    
    
