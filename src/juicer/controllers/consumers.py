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

from juicer.controllers.base import JSONController
from juicer.runtime import config
from pulp.api.consumer import ConsumerApi

# consumers api ---------------------------------------------------------------

api = ConsumerApi(config)
log = logging.getLogger('pulp')
             
# controllers -----------------------------------------------------------------
    
class Consumers(JSONController):

    @JSONController.error_handler
    def GET(self):
        """
        List all available consumers.
        @return: a list of all consumers
        """
        filters = self.filters(['package_name'])
        log.debug("Filters: %s" % filters)
        if len(filters) == 1:
            pkgname = filters.get('package_name')[0]
            if pkgname:
                log.debug("calling consumers_with_package_name(pkgname): %s" %
                          pkgname)
                result = api.consumers_with_package_name(pkgname)
                if (log.level == logging.DEBUG):
                    log.debug("result from consumers_with_package_name: %s"
                           % result)
                return self.ok(result)
            else:
                return self.ok([])
        return self.ok(api.consumers())
     
    @JSONController.error_handler
    def PUT(self):
        """
        Create a new consumer.
        @return: consumer meta data on successful creation of consumer
        """
        consumer_data = self.params()
        consumer = api.create(consumer_data['id'], consumer_data['description'])
        path = self.extend_path(consumer.id)
        return self.created(path, consumer)

    @JSONController.error_handler
    def DELETE(self):
        """
        @return: True on successful deletion of all consumers
        """
        api.clean()
        return self.ok(True)
    

class Bulk(JSONController):
    # XXX this class breaks the restful practices.... (need a better solution)
    @JSONController.error_handler
    def POST(self):
        api.bulkcreate(self.params())
        return self.ok(True)

 
class Consumer(JSONController):

    @JSONController.error_handler
    def GET(self, id):
        """
        Get a consumer's meta data.
        @param id: consumer id
        @return: consumer meta data
        """
        return self.ok(api.consumer(id))
    
    @JSONController.error_handler
    def PUT(self, id):
        """
        Update consumer
        @param id: The consumer id
        @type id: str
        """
        consumer = self.params()
        consumer = api.update(consumer)
        return self.ok(True)

    @JSONController.error_handler
    def DELETE(self, id):
        """
        Delete a consumer.
        @param id: consumer id
        @return: True on successful deletion of consumer
        """
        api.delete(id=id)
        return self.ok(True)


class ConsumerDeferredFields(JSONController):
    
    # NOTE the intersection of exposed_fields and exposed_actions must be empty
    exposed_fields = (
        'packages',
    )
    
    def packages(self, id):
        """
        Get a consumer's set of packages
        @param id: consumer id
        @return: consumer's installed packages
        """
        valid_filters = ('name', 'arch')
        filters = self.filters(valid_filters)
        packages = api.packages(id)
        filtered_packages = self.filter_results(packages, filters)
        return self.ok(filtered_packages)
    
    @JSONController.error_handler
    def GET(self, id, field_name):
        field = getattr(self, field_name, None)
        if field is None:
            return self.internal_server_error('No implementation for %s found' % field_name)
        return field(id)
    

class ConsumerActions(JSONController):
    
    # See juicer.repositories.RepositoryActions for design
    
    # NOTE the intersection of exposed_actions and exposed_fields must be empty
    exposed_actions = (
        'bind',
        'unbind',
        'profile',
        'installpackages',
    )
    
    def bind(self, id):
        """
        Bind (subscribe) a user to a repository.
        @param id: consumer id
        """
        data = self.params()
        api.bind(id, data)
        return self.ok(True)

    def unbind(self, id):
        """
        Unbind (unsubscribe) a user to a repository.
        @param id: consumer id
        """
        data = self.params()
        api.unbind(id, data)
        return self.ok(None)
    
    def profile(self, id):
        """
        update/add Consumer profile information. eg:package, hardware etc
        """
        api.profile_update(id, self.params())
        return self.ok(True)

    def installpackages(self, id):
        """
        Install packages.
        Body contains a list of package names.
        """
        data = self.params()
        names = data.get('packagenames', [])
        return self.ok(api.installpackages(id, names))
        
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
    
    '/([^/]+)/(%s)/$' % '|'.join(ConsumerDeferredFields.exposed_fields),
    'ConsumerDeferredFields',
    
    '/([^/]+)/(%s)/$' % '|'.join(ConsumerActions.exposed_actions),
    'ConsumerActions',
)

application = web.application(URLS, globals())
