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
from pulp.server.api.repo import RepoApi
from pulp.server.api.user import UserApi
from pulp.server.auth.authorization import (
    revoke_all_permissions_from_user, grant_permission_to_user,
    grant_auto_permissions_for_created_resource,
    add_user_to_role, consumer_users_role)
from pulp.server.webservices import http
from pulp.server.webservices import mongo
from pulp.server.webservices.controllers.base import JSONController, AsyncController
from pulp.server.webservices.role_check import RoleCheck

# globals ---------------------------------------------------------------------

consumer_api = ConsumerApi()
history_api = ConsumerHistoryApi()
repo_api = RepoApi()
user_api = UserApi()
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
    def POST(self):
        """
        Create a new consumer.
        @return: consumer meta data on successful creation of consumer
        """
        consumer_data = self.params()
        id = consumer_data['id']
        consumer = consumer_api.consumer(id)
        if consumer is not None:
            return self.conflict('Consumer with id: %s already exists' % id)
        user = user_api.user(id)
        if user is not None:
            return self.conflict(
                'Cannot create corresponding auth credentials: user with id %s alreay exists' % id)
        consumer = consumer_api.create(id, consumer_data['description'],
                                       consumer_data['key_value_pairs'])
        # create corresponding user for auth credentials
        user = user_api.create(id)
        add_user_to_role(consumer_users_role, user['login'])
        # grant the appropriate permissions to the user
        path = http.extend_uri_path(consumer.id) # path for consumer resource
        resource = http.resource_path(path)
        grant_permission_to_user(resource, id,
                                 ('READ', 'UPDATE', 'DELETE', 'EXECUTE'))
        grant_auto_permissions_for_created_resource(resource)
        return self.created(path, consumer)

    def PUT(self):
        log.debug('deprecated Consumers.PUT method called')
        return self.POST()

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
        consumer = consumer_api.consumer(id)
        if consumer is None:
            return self.conflict('Consumer [%s] does not exist' % id)
        user = user_api.user(id)
        if user is not None:
            revoke_all_permissions_from_user(user['login'])
            user_api.delete(login=id)
        consumer_api.delete(id=id)
        return self.ok(True)


class ConsumerDeferredFields(JSONController):

    # NOTE the intersection of exposed_fields and exposed_actions must be empty
    exposed_fields = (
        'package_profile',
        'repoids',
        'certificate',
        'keyvalues',
        'package_updates',
        'errata_package_updates'
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

    @RoleCheck(admin=True)
    def keyvalues(self, id):
        """
        Get key-value pairs for this consumer. This also includes attributes
        inherited from consumergroup.
        @type id: str ID of the Consumer
        @param id: consumer id
        @return: Key-value attributes  
        """
        keyvalues = consumer_api.get_keyvalues(id)
        return self.ok(keyvalues)

    @JSONController.error_handler
    @RoleCheck(consumer_id=True, admin=True)
    def package_updates(self, id):
        """
        list applicable package updates for a given consumerid.
        @type id: str
        @param id: consumer id
        """
        return self.ok(consumer_api.list_package_updates(id)['packages'])

    @JSONController.error_handler
    @RoleCheck(consumer_id=True, admin=True)
    def errata_package_updates(self, id):
        """
        Return applicable errata and package updates for a given consumerid.
        @type id: str
        @param id: consumer id
        """
        return self.ok(consumer_api.list_errata_package(id))

    @JSONController.error_handler
    def GET(self, id, field_name):
        """
        Deferred field dispatcher.
        """
        field = getattr(self, field_name, None)
        if field is None:
            return self.internal_server_error('No implementation for %s found' % field_name)
        return field(id)


class ConsumerActions(AsyncController):

    # See pulp.webservices.repositories.RepositoryActions for design

    # NOTE the intersection of exposed_actions and exposed_fields must be empty
    exposed_actions = (
        'bind',
        'unbind',
        'add_key_value_pair',
        'delete_key_value_pair',
        'update_key_value_pair',
        'profile',
        'installpackages',
        'installpackagegroups',
        'installpackagegroupcategories',
        'listerrata',
        'installerrata',
        'history',
    )


    def validate_consumer(self, id):
        if not consumer_api.consumer(id):
            return False
        else:
            return True

    @RoleCheck(consumer_id=True, admin=True)
    def bind(self, id):
        """
        Bind (subscribe) a user to a repository.
        @type id: str
        @param id: consumer id
        """
        data = self.params()
        if not repo_api.repository(data):
            return self.conflict('Repo [%s] does not exist' % data)
        consumer_api.bind(id, data)
        return self.ok(True)

    @RoleCheck(consumer_id=True, admin=True)
    def unbind(self, id):
        """
        Unbind (unsubscribe) a user to a repository.
        @type id: str
        @param id: consumer id
        """
        data = self.params()
        if not repo_api.repository(data):
            return self.conflict('Repo [%s] does not exist' % data)
        consumer_api.unbind(id, data)
        return self.ok(None)

    @RoleCheck(consumer_id=True, admin=True)
    def add_key_value_pair(self, id):
        """
        Add key-value information to consumer.
        @type id: str
        @param id: consumer id
        
        """
        data = self.params()
        consumer = consumer_api.consumer(id)
        key_value_pairs = consumer['key_value_pairs']
        if data['key'] in key_value_pairs.keys():
            return self.conflict('Given key [%s] already exist' % data['key'])
        consumer_api.add_key_value_pair(id, data['key'], data['value'])
        return self.ok(True)

    @RoleCheck(consumer_id=True, admin=True)
    def delete_key_value_pair(self, id):
        """
        Delete key-value information from consumer.
        @type id: str
        @param id: consumer id
        
        """
        data = self.params()
        consumer = consumer_api.consumer(id)
        key_value_pairs = consumer['key_value_pairs']
        if data not in key_value_pairs.keys():
            return self.conflict('Given key [%s] does not exist' % data)
        consumer_api.delete_key_value_pair(id, data)
        return self.ok(True)

    @RoleCheck(consumer_id=True, admin=True)
    def update_key_value_pair(self, id):
        """
        Update key-value information of a consumer.
        @type id: str
        @param id: consumer id
        
        """
        data = self.params()
        consumer = consumer_api.consumer(id)
        key_value_pairs = consumer['key_value_pairs']
        if data['key'] not in key_value_pairs.keys():
            return self.conflict('Given key [%s] does not exist' % data['key'])
        consumer_api.update_key_value_pair(id, data['key'], data['value'])
        return self.ok(True)

    @RoleCheck(consumer_id=True, admin=True)
    def profile(self, id):
        """
        update/add Consumer profile information. eg:package, hardware etc
        @type id: str
        @param id: consumer id
        """
        log.debug("consumers.py profile() with id: %s" % id)
        consumer_api.profile_update(id, self.params())
        return self.ok(True)

    @RoleCheck(consumer_id=True, admin=True)
    def installpackages(self, id):
        """
        Install packages.
        Body contains a list of package names.
        @type id: str
        @param id: consumer id
        """
        data = self.params()
        names = data.get('packagenames', [])
        task = consumer_api.installpackages(id, names)
        if data.has_key("scheduled_time"):
            task.scheduled_time = data["scheduled_time"]
        taskdict = self._task_to_dict(task)
        taskdict['status_path'] = self._status_path(task.id)
        return self.accepted(taskdict)

    @RoleCheck(consumer_id=True, admin=True)
    def installpackagegroups(self, id):
        """
        Install package groups.
        Body contains a list of package ids.
        @type id: str
        @param id: consumer id
        """
        data = self.params()
        ids = data.get('packageids', [])
        task = consumer_api.installpackagegroups(id, ids)
        if data.has_key("scheduled_time"):
            task.scheduled_time = data["scheduled_time"]
        taskdict = self._task_to_dict(task)
        taskdict['status_path'] = self._status_path(task.id)
        return self.accepted(taskdict)

    @RoleCheck(consumer_id=True, admin=True)
    def installpackagegroupcategories(self, id):
        """
        Install package group categories.
        Body contains a list of package group category ids.
        @type id: str
        @param id: consumer id
        """
        data = self.params()
        categoryids = data.get('categoryids', [])
        repo_id = data.get('repoid')
        if not repo_id:
            return self.conflict('No repository id was passed in.')
        group_ids = []
        for cat_id in categoryids:
            pkggrpcat = repo_api.packagegroupcategory(repo_id, cat_id)
            if not pkggrpcat:
                return self.conflict('Given category id [%s] in repo [%s] does not exist' % (cat_id, repo_id))
            group_ids.extend(pkggrpcat['packagegroupids'])
        if not group_ids:
            return self.conflict('Given category ids [%s] contain no groups to install' % categoryids)
        task = consumer_api.installpackagegroups(id, group_ids)
        if data.has_key("scheduled_time"):
            task.scheduled_time = data["scheduled_time"]
        taskdict = self._task_to_dict(task)
        taskdict['status_path'] = self._status_path(task.id)
        return self.accepted(taskdict)

    @JSONController.error_handler
    @RoleCheck(consumer_id=True, admin=True)
    def installerrata(self, id):
        """
        Install errata
        Body contains list of errata ids and/or type
        @type id: str
        @param id: consumer id
        """
        data = self.params()
        eids = data.get('errataids', [])
        types = data.get('types', [])
        assumeyes = data.get('assumeyes', False)
        task = consumer_api.installerrata(id, eids, types, assumeyes)
        if not task:
            return self.not_found('Errata %s you requested is not applicable for your system' % id)
        if data.has_key("scheduled_time"):
            task.scheduled_time = data["scheduled_time"]
        taskdict = self._task_to_dict(task)
        taskdict['status_path'] = self._status_path(task.id)
        return self.accepted(taskdict)

    @JSONController.error_handler
    @RoleCheck(consumer_id=True, admin=True)
    def listerrata(self, id):
        """
        list applicable errata for a given repo.
        filter by errata type if any
        @type id: str
        @param id: consumer id
        """
        data = self.params()
        return self.ok(consumer_api.listerrata(id, data['types']))

    @JSONController.error_handler
    @RoleCheck(consumer_id=True, admin=True)
    def history(self, id):
        """
        @type id: str
        @param id: consumer id
        """
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

        # The date inputs only specify to the day, but in order to appropriately describe
        # the full day we need to set the start/end times to the start and end of the days.
        # This is more relevant in the end_date case, which will omit that day if this
        # step isn't taken (see BZ 638715).

        if start_date:
            start_date = datetime.datetime.strptime(start_date + '-00-00-00', '%Y-%m-%d-%H-%M-%S')

        if end_date:
            end_date = datetime.datetime.strptime(end_date + '-23-59-59', '%Y-%m-%d-%H-%M-%S')

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
        if not self.validate_consumer(id):
            return self.conflict('Consumer [%s] does not exist' % id)
        return action(id)


class ConsumerActionStatus(AsyncController):

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def GET(self, id, action_name, action_id):
        """
        Check the status of a package install operation.
        @param id: repository id
        @param action_name: name of the action
        @param action_id: action id
        @return: action status information
        """
        task_info = self.task_status(action_id)
        if task_info is None:
            return self.not_found('No %s with id %s found' % (action_name, action_id))
        return self.ok(task_info)


# web.py application ----------------------------------------------------------

URLS = (
    '/$', 'Consumers',
    '/bulk/$', 'Bulk',
    '/([^/]+)/$', 'Consumer',

    '/([^/]+)/(%s)/$' % '|'.join(ConsumerDeferredFields.exposed_fields),
    'ConsumerDeferredFields',

    '/([^/]+)/(%s)/$' % '|'.join(ConsumerActions.exposed_actions),
    'ConsumerActions',

    '/([^/]+)/(%s)/([^/]+)/$' % '|'.join(ConsumerActions.exposed_actions),
    'ConsumerActionStatus',
)

application = web.application(URLS, globals())
