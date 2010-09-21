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

import datetime
import itertools
import logging

import web

from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.consumer_history import ConsumerHistoryApi, SORT_DESCENDING
from pulp.server.webservices import http
from pulp.server.webservices import mongo
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.role_check import RoleCheck

# globals ---------------------------------------------------------------------

consumer_api = ConsumerApi()
history_api = ConsumerHistoryApi()
log = logging.getLogger('pulp')

# default fields for consumers being sent to a client
default_fields = ['id', 'description', 'key_value_pairs']
             
# controllers -----------------------------------------------------------------
    
class Consumers(JSONController):

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def GET(self):
        """
        List all available consumers.
        @return: a list of all consumers
        """
        valid_filters = ('id', 'package_name')
        filters = self.filters(valid_filters)
        package_names = filters.pop('package_name', None)
        if package_names is not None:
            result = consumer_api.consumers_with_package_names(package_names, default_fields)
            consumers = self.filter_results(result, filters)
        else:
            spec = mongo.filters_to_re_spec(filters)
            consumers = consumer_api.consumers(spec, default_fields)
        # add the uri ref and deferred fields
        for c in consumers:
            c['uri_ref'] = http.extend_uri_path(c['id'])
            for f in ConsumerDeferredFields.exposed_fields:
                c[f] = http.extend_uri_path('/'.join((c['id'], f)))
        return self.ok(consumers)
     
    @JSONController.error_handler
    @RoleCheck(admin=True)
    def PUT(self):
        """
        Create a new consumer.
        @return: consumer meta data on successful creation of consumer
        """
        consumer_data = self.params()
        id = consumer_data['id']
        consumer = consumer_api.consumer(id)
        if consumer is not None:
            return self.conflict('Consumer with id: %s, already exists' % id)
        consumer = consumer_api.create(id, consumer_data['description'], 
                                       consumer_data['key_value_pairs'])
        path = http.extend_uri_path(consumer.id)
        return self.created(path, consumer)

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def DELETE(self):
        """
        Delete all consumers.
        @return: True on successful deletion of all consumers
        """
        consumer_api.clean()
        return self.ok(True)
    

class Bulk(JSONController):
    # XXX this class breaks the restful practices.... (need a better solution)
    @JSONController.error_handler
    @RoleCheck(admin=True)
    def POST(self):
        consumer_api.bulkcreate(self.params())
        return self.ok(True)

 
class Consumer(JSONController):

    @JSONController.error_handler
    @RoleCheck(consumer_id=True, admin=True)
    def GET(self, id):
        """
        Get a consumer's meta data.
        @param id: consumer id
        @return: consumer meta data
        """
        consumer = consumer_api.consumer(id, fields=default_fields)
        if consumer is None:
            return self.not_found('No consumer %s' % id)
        consumer['uri_ref'] = http.uri_path()
        for field in ConsumerDeferredFields.exposed_fields:
            consumer[field] = http.extend_uri_path(field)
        return self.ok(consumer)
    
    @JSONController.error_handler
    @RoleCheck(admin=True)
    def PUT(self, id):
        """
        Update consumer
        @param id: The consumer id
        @type id: str
        """
        log.debug("PUT called.")
        consumer_data = self.params()
        if id != consumer_data['id']:
            return self.bad_request('Cannot change the consumer id')
        # remove the deferred fields as they are not manipulated via this method
        for field in itertools.chain(['uri_ref'], # web services only field
                                     ConsumerDeferredFields.exposed_fields):
            consumer_data.pop(field, None)
        consumer_api.update(consumer_data)
        return self.ok(True)

    @JSONController.error_handler
    @RoleCheck(consumer_id=True, admin=True)
    def DELETE(self, id):
        """
        Delete a consumer.
        @param id: consumer id
        @return: True on successful deletion of consumer
        """
        consumer_api.delete(id=id)
        return self.ok(True)


class ConsumerDeferredFields(JSONController):
    
    # NOTE the intersection of exposed_fields and exposed_actions must be empty
    exposed_fields = (
        'package_profile',
        'repoids',
        'certificate'
    )
    @RoleCheck(consumer_id=True, admin=True)
    def package_profile(self, id):
        """
        Get a consumer's set of packages
        @param id: consumer id
        @return: consumer's installed packages
        """
        valid_filters = ('name', 'arch')
        filters = self.filters(valid_filters)
        packages = consumer_api.packages(id)
        packages = self.filter_results(packages, filters)
        return self.ok(packages)
    
    @RoleCheck(consumer_id=True, admin=True)
    def repoids(self, id):
        """
        Get the ids of the repositories the consumer is bound to.
        @type id: str
        @param id: consumer id
        @return: dict of repository id: uri reference
        """
        valid_filters = ('id')
        filters = self.filters(valid_filters)
        consumer = consumer_api.consumer(id, fields=['repoids'])
        repoids = self.filter_results(consumer['repoids'], filters)
        repo_data = dict((id, '/repositories/%s/' % id) for id in repoids)
        return self.ok(repo_data)   
   
    @RoleCheck(admin=True)
    def certificate(self, id):
        """
        Get a X509 Certificate for this Consumer.  Useful for uniquely and securely 
        identifying this Consumer later.
        @type id: str ID of the Consumer
        @param id: consumer id
        @return: X509 PEM Certificate
        """
        valid_filters = ('id')
        filters = self.filters(valid_filters)
        private_key, certificate = consumer_api.certificate(id)
        certificate = {'certificate': certificate, 'private_key': private_key}
        return self.ok(certificate)

    @JSONController.error_handler
    def GET(self, id, field_name):
        """
        Deferred field dispatcher.
        """
        field = getattr(self, field_name, None)
        if field is None:
            return self.internal_server_error('No implementation for %s found' % field_name)
        return field(id)
    

class ConsumerActions(JSONController):
    
    # See pulp.webservices.repositories.RepositoryActions for design
    
    # NOTE the intersection of exposed_actions and exposed_fields must be empty
    exposed_actions = (
        'bind',
        'unbind',
        'profile',
        'installpackages',
        'installpackagegroups',
        'listerrata',
        'installerrata',
        'history',
    )
    
    @RoleCheck(consumer_id=True, admin=True)
    def bind(self, id):
        """
        Bind (subscribe) a user to a repository.
        @param id: consumer id
        """
        data = self.params()
        consumer_api.bind(id, data)
        return self.ok(True)
    
    @RoleCheck(consumer_id=True, admin=True)
    def unbind(self, id):
        """
        Unbind (unsubscribe) a user to a repository.
        @param id: consumer id
        """
        data = self.params()
        consumer_api.unbind(id, data)
        return self.ok(None)
    
    @RoleCheck(consumer_id=True, admin=True)
    def profile(self, id):
        """
        update/add Consumer profile information. eg:package, hardware etc
        """
        log.debug("consumers.py profile() with id: %s" % id)
        consumer_api.profile_update(id, self.params())
        return self.ok(True)

    @RoleCheck(consumer_id=True, admin=True)
    def installpackages(self, id):
        """
        Install packages.
        Body contains a list of package names.
        """
        data = self.params()
        names = data.get('packagenames', [])
        return self.ok(consumer_api.installpackages(id, names))
    
    @RoleCheck(consumer_id=True, admin=True)
    def installpackagegroups(self, id):
        """
        Install package groups.
        Body contains a list of package ids.
        """
        data = self.params()
        ids = data.get('packageids', [])
        return self.ok(consumer_api.installpackagegroups(id, ids))

    @RoleCheck(consumer_id=True, admin=True)
    def installerrata(self, id):
        """
        Install errata
        Body contains list of errata ids and/or type
        """
        data = self.params()
        eids = data.get('errataids', [])
        types = data.get('types', [])
        return self.ok(consumer_api.installerrata(id, eids, types))

    @JSONController.error_handler
    @RoleCheck(consumer_id=True, admin=True)
    def listerrata(self, id):
        """
         list applicable errata for a given repo.
         filter by errata type if any
        """
        data = self.params()
        return self.ok(consumer_api.listerrata(id, data['types']))

    @JSONController.error_handler
    @RoleCheck(consumer_id=True, admin=True)
    def history(self, id):
        data = self.params()

        event_type = data.get('event_type', None)
        limit = data.get('limit', None)
        sort = data.get('sort', None)
        start_date = data.get('start_date', None)
        end_date = data.get('end_date', None)

        if sort is None:
            sort = SORT_DESCENDING

        if limit:
            limit = int(limit)

        if start_date:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')

        if end_date:
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')

        results = history_api.query(consumer_id=id, event_type=event_type, limit=limit,
                                    sort=sort, start_date=start_date, end_date=end_date)
        return self.ok(results)

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
        log.debug("consumers.py POST.  Action: %s" % action_name)
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
