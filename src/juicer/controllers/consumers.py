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
from pulp.api.consumer import ConsumerApi

API = ConsumerApi(None)

# web.py application ----------------------------------------------------------

URLS = (
    '/$', 'Consumers',
    '/([^/]+)/$', 'Consumer',
    '/(\d+)/subscribe/(\d+)', 'Subscribe',
)

application = web.application(URLS, globals())

# queries ---------------------------------------------------------------------
    
class Consumers(JSONController):
    """
    List all consumers.
    """
    def GET(self):
        """
        @return: a list of all consumers
        """
        return self.output(API.consumers())
    
# actions ---------------------------------------------------------------------
 
class Consumer(JSONController):

    def POST(self):
        """
        @return: consumer meta data on successful creation of consumer
        """
        consumer_data = self.input()
        consumer = API.create(consumer_data['id'], consumer_data['description'])
        return self.output(consumer)

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

class Subscribe(object):
    """
    Subscribe a user to a repository.
    """
    def POST(self, consumer_id, repo_id):
        pass
    
    
