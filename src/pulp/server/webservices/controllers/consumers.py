# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import itertools
import logging
#from datetime import datetime
from gettext import gettext as _

import web

from pulp.common import dateutils
from pulp.server import async
from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.consumer_history import ConsumerHistoryApi, SORT_DESCENDING
from pulp.server.api.repo import RepoApi

from pulp.server.api.user import UserApi
from pulp.server.auth.authorization import (
    revoke_all_permissions_from_user, add_user_to_role, consumer_users_role,
    grant_automatic_permissions_for_created_resource,
    grant_automatic_permissions_to_consumer_user,
    CREATE, READ, UPDATE, DELETE, EXECUTE)
from pulp.server.tasking.scheduler import AtScheduler
from pulp.server.webservices import http
from pulp.server.webservices import mongo
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import (
    auth_required, error_handler)
from pulp.server.gc_agent import PulpAgent

# Temporary hack to use V2 repositories with V1 consumers. This will be removed once consumers are migrated to V2.
from pulp.server.db.model.gc_repository import Repo
from pulp.server.exceptions import MissingResource

# globals ---------------------------------------------------------------------

consumer_api = ConsumerApi()
history_api = ConsumerHistoryApi()
repo_api = RepoApi()
user_api = UserApi()
log = logging.getLogger('pulp')

# default fields for consumers being sent to a client
default_fields = ['id', 'description', 'capabilities', 'key_value_pairs',]

# controllers -----------------------------------------------------------------

class Consumers(JSONController):

    @error_handler
    @auth_required(READ)
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
        # inject heartbeat info
        for c in consumers:
            uuid = c['id']
            heartbeat = PulpAgent.status([uuid, ])
            c['heartbeat'] = heartbeat.values()[0]
        # add the uri ref and deferred fields
        for c in consumers:
            c['uri_ref'] = http.extend_uri_path(c['id'])
            for f in ConsumerDeferredFields.exposed_fields:
                c[f] = http.extend_uri_path('/'.join((c['id'], f)))
        return self.ok(consumers)

    @error_handler
    @auth_required(CREATE)
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
        consumer = \
            consumer_api.create(
                id,
                consumer_data['description'],
                capabilities=consumer_data.get('capabilities', {}),
                key_value_pairs=consumer_data.get('key_value_pairs', {}))
        # create corresponding user for auth credentials
        user = user_api.create(id)
        add_user_to_role(consumer_users_role, user['login'])
        grant_automatic_permissions_to_consumer_user(user['login'])
        # grant the appropriate permissions for the user
        path = http.extend_uri_path(consumer.id) # url path for consumer
        resource = http.resource_path(path) # path for consumer resource
        grant_automatic_permissions_for_created_resource(resource)
        return self.created(path, consumer)

    def PUT(self):
        log.debug('deprecated Consumers.PUT method called')
        return self.POST()

    @error_handler
    @auth_required(DELETE)
    def DELETE(self):
        """
        Delete all consumers.
        @return: True on successful deletion of all consumers
        """
        consumer_api.clean()
        return self.ok(True)


class Bulk(JSONController):
    # XXX this class breaks the restful practices.... (need a better solution)
    @error_handler
    @auth_required(CREATE)
    def POST(self):
        consumer_api.bulkcreate(self.params())
        return self.ok(True)


class Consumer(JSONController):

    @error_handler
    @auth_required(READ)
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
        # inject heartbeat info
        heartbeat = PulpAgent.status([id, ])
        consumer['heartbeat'] = heartbeat.values()[0]
        return self.ok(consumer)

    @error_handler
    @auth_required(UPDATE)
    def PUT(self, id):
        """
        Update consumer
        @param id: The consumer id
        @type id: str
        """
        log.debug("PUT called.")
        delta = self.params()
        if id != delta.pop('id', id):
            return self.bad_request('Cannot change the consumer id')
        # remove the deferred fields as they are not manipulated via this method
        for field in itertools.chain(['uri_ref'], # web services only field
                                     ConsumerDeferredFields.exposed_fields):
            delta.pop(field, None)
        consumer_api.update(id, delta)
        return self.ok(True)

    @error_handler
    @auth_required(DELETE)
    def DELETE(self, id):
        """
        Delete a consumer.
        @param id: consumer id
        @return: True on successful deletion of consumer
        """
        consumer = consumer_api.consumer(id)
        if consumer is None:
            return self.not_found('Consumer [%s] does not exist' % id)
        user = user_api.user(id)
        if user is not None:
            revoke_all_permissions_from_user(user['login'])
            user_api.delete(login=id)
        # Unbind the consumer from all repos
        for repo_id in consumer["repoids"]:
            consumer_api.unbind(id, repo_id)
        consumer_api.delete(id=id)
        return self.ok(True)


class ConsumerDeferredFields(JSONController):

    # NOTE the intersection of exposed_fields and exposed_actions must be empty
    exposed_fields = (
        'package_profile',
        'repoids',
        'keyvalues',
        'package_updates',
        'errata_package_updates',
        'errata',
    )

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

    def package_updates(self, id):
        """
        list applicable package updates for a given consumerid.
        @type id: str
        @param id: consumer id
        """
        return self.ok(consumer_api.list_package_updates(id)['packages'])

    def errata_package_updates(self, id):
        """
        Return applicable errata and package updates for a given consumerid.
        @type id: str
        @param id: consumer id
        """
        return self.ok(consumer_api.list_errata_package(id))

    def errata(self, id):
        """
        list applicable errata for a given consumer.
        filter by errata type if any
        @type id: str
        @param id: consumer id
        """
        if not consumer_api.consumer(id):
            return self.conflict('Consumer [%s] does not exist' % id)
        valid_filters = ('types')
        types = self.filters(valid_filters).get('type', [])
           
        if types == []:
            errataids = consumer_api.listerrata(id)
        else:
            errataids = consumer_api.listerrata(id, [types])
        return self.ok(errataids)

    @error_handler
    @auth_required(READ)
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
        'add_key_value_pair',
        'delete_key_value_pair',
        'update_key_value_pair',
        'installpackages',
        'updatepackages',
        'uninstallpackages',
        'installpackagegroups',
        'uninstallpackagegroups',
        'installpackagegroupcategories',
        'installerrata',
        'history',
    )


    def validate_consumer(self, id):
        if not consumer_api.consumer(id):
            return False
        else:
            return True

    def bind(self, id):
        """
        Bind (subscribe) a user to a repository.
        @type id: str
        @param id: consumer id
        """
        data = self.params()

# <V2 Repo changes>
        repo = Repo.get_collection().find_one({'id' : data})
        if repo is None:
            raise MissingResource(data)
#        if not repo_api.repository(data):
#            return self.not_found('Repo [%s] does not exist' % data)
# </V2 Repo changes>

        bind_data = consumer_api.bind(id, data)
        return self.ok(bind_data)

    def unbind(self, id):
        """
        Unbind (unsubscribe) a user to a repository.
        @type id: str
        @param id: consumer id
        """
        data = self.params()
# <V2 Repo changes>
        repo = Repo.get_collection().find_one({'id' : data})
        if repo is None:
            raise MissingResource(data)
#        if not repo_api.repository(data):
#            return self.not_found('Repo [%s] does not exist' % data)
# </V2 Repo changes>
        consumer_api.unbind(id, data)
        return self.ok(True)

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
            return self.not_found('Given key [%s] does not exist' % data)
        consumer_api.delete_key_value_pair(id, data)
        return self.ok(True)

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
            return self.not_found('Given key [%s] does not exist' % data['key'])
        consumer_api.update_key_value_pair(id, data['key'], data['value'])
        return self.ok(True)

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
        scheduled_time = data.get('scheduled_time', None)
        if scheduled_time is not None:
            scheduled_time = dateutils.parse_iso8601_datetime(scheduled_time)
            scheduled_time = dateutils.to_utc_datetime(scheduled_time)
            task.scheduler = AtScheduler(scheduled_time)
        async.enqueue(task, unique=False)
        taskdict = self._task_to_dict(task)
        return self.accepted(taskdict)

    def updatepackages(self, id):
        """
        Update packages.
        Body contains a list of package names.
        @type id: str
        @param id: consumer id
        """
        data = self.params()
        names = data.get('packagenames', [])
        task = consumer_api.updatepackages(id, names)
        scheduled_time = data.get('scheduled_time', None)
        if scheduled_time is not None:
            scheduled_time = dateutils.parse_iso8601_datetime(scheduled_time)
            scheduled_time = dateutils.to_utc_datetime(scheduled_time)
            task.scheduler = AtScheduler(scheduled_time)
        async.enqueue(task, unique=False)
        taskdict = self._task_to_dict(task)
        return self.accepted(taskdict)

    def uninstallpackages(self, id):
        """
        Uninstall packages.
        Body contains a list of package names.
        @type id: str
        @param id: consumer id
        """
        data = self.params()
        names = data.get('packagenames', [])
        task = consumer_api.uninstallpackages(id, names)
        scheduled_time = data.get('scheduled_time', None)
        if scheduled_time is not None:
            scheduled_time = dateutils.parse_iso8601_datetime(scheduled_time)
            scheduled_time = dateutils.to_utc_datetime(scheduled_time)
            task.scheduler = AtScheduler(scheduled_time)
        async.enqueue(task, unique=False)
        taskdict = self._task_to_dict(task)
        return self.accepted(taskdict)

    def installpackagegroups(self, id):
        """
        Install package groups.
        Body contains a list of package ids.
        @type id: str
        @param id: consumer id
        """
        data = self.params()
        ids = data.get('groupids', [])
        task = consumer_api.installpackagegroups(id, ids)
        scheduled_time = data.get('scheduled_time', None)
        if scheduled_time is not None:
            scheduled_time = dateutils.parse_iso8601_datetime(scheduled_time)
            scheduled_time = dateutils.to_utc_datetime(scheduled_time)
            task.scheduler = AtScheduler(scheduled_time)
        async.enqueue(task, unique=False)
        taskdict = self._task_to_dict(task)
        return self.accepted(taskdict)

    def uninstallpackagegroups(self, id):
        """
        Unnstall package groups.
        Body contains a list of package ids.
        @type id: str
        @param id: consumer id
        """
        data = self.params()
        ids = data.get('groupids', [])
        task = consumer_api.uninstallpackagegroups(id, ids)
        scheduled_time = data.get('scheduled_time', None)
        if scheduled_time is not None:
            scheduled_time = dateutils.parse_iso8601_datetime(scheduled_time)
            scheduled_time = dateutils.to_utc_datetime(scheduled_time)
            task.scheduler = AtScheduler(scheduled_time)
        async.enqueue(task, unique=False)
        taskdict = self._task_to_dict(task)
        return self.accepted(taskdict)

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
        scheduled_time = data.get('scheduled_time', None)
        if scheduled_time is not None:
            scheduled_time = dateutils.parse_iso8601_datetime(scheduled_time)
            scheduled_time = dateutils.to_utc_datetime(scheduled_time)
            task.scheduler = AtScheduler(scheduled_time)
        async.enqueue(task, unique=False)
        taskdict = self._task_to_dict(task)
        return self.accepted(taskdict)

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
        importkeys = data.get('importkeys', False)
        task = consumer_api.installerrata(id, eids, types, importkeys)
        if not task:
            return self.not_found('Errata %s you requested are not applicable for your system' % eids)
        scheduled_time = data.get('scheduled_time', None)
        if scheduled_time is not None:
            scheduled_time = dateutils.parse_iso8601_datetime(scheduled_time)
            scheduled_time = dateutils.to_utc_datetime(scheduled_time)
            task.scheduler = AtScheduler(scheduled_time)
        async.enqueue(task, unique=False)
        taskdict = self._task_to_dict(task)
        return self.accepted(taskdict)

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
            start_date = dateutils.parse_datetime(start_date + '-00-00-00')
            start_date = dateutils.to_local_datetime(start_date)

        if end_date:
            end_date = dateutils.parse_datetime(end_date + '-23-59-59')
            end_date = dateutils.to_local_datetime(end_date)

        results = history_api.query(consumer_id=id, event_type=event_type, limit=limit,
                                    sort=sort, start_date=start_date, end_date=end_date)
        return self.ok(results)

    @error_handler
    @auth_required(EXECUTE)
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
            return self.not_found('Consumer [%s] does not exist' % id)
        return action(id)


class ConsumerProfileUpdate(JSONController):

    @error_handler
    @auth_required(UPDATE)
    def PUT(self, id):
        """
        Update consumer's profile information
        @param id: The consumer id
        @type id: str
        """
        log.debug("PUT called on consumer profile update")
        delta = self.params()
        consumer = consumer_api.consumer(id)
        if consumer is None:
            return self.bad_request('Consumer [%s] does not exist' % id)
        if id != delta.pop('id', id):
            return self.bad_request('Cannot change the consumer id')
        if not delta.has_key('package_profile') or not len(delta['package_profile']):
            self.bad_request('No package profile information found for consumer [%s].' % id)
        log.debug("Updating consumer Profile %s" % delta['package_profile'])
        consumer_api.profile_update(id, delta['package_profile'])
        return self.ok(True)

    def GET(self, id):
        """
        Get a consumer's set of packages
        @param id: consumer id
        @return: consumer's installed packages
        """
        consumer = consumer_api.consumer(id)
        if consumer is None:
            return self.bad_request('Consumer [%s] does not exist' % id)
        valid_filters = ('name', 'arch')
        filters = self.filters(valid_filters)
        packages = consumer_api.packages(id)
        packages = self.filter_results(packages, filters)
        return self.ok(packages)


class ApplicableErrataInRepos(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self):
        """
        List all errata associated with a group of repositories along with consumers that it is applicable to
        @param repoids: repository ids
        @return: list of object that are mappings of errata id in given repoids to applicable consumers
        """
        valid_filters = ('repoids','send_only_applicable_errata',)
        filters = self.filters(valid_filters)
        repoids = filters.pop('repoids', [])
        send_only_applicable_errata = filters.pop('send_only_applicable_errata', ['true'])
        if send_only_applicable_errata[0] not in ['true','false']:
            return self.bad_request("Invalid input for send_only_applicable_errata. Accepted inputs are 'true' or 'false'")
        errata = consumer_api.get_consumers_applicable_errata(repoids, send_only_applicable_errata[0])
        return self.ok(errata)



# web.py application ----------------------------------------------------------

URLS = (
    '/$', 'Consumers',
    '/applicable_errata_in_repos/$', 'ApplicableErrataInRepos',
    '/bulk/$', 'Bulk',
    '/([^/]+)/$', 'Consumer',
    '/([^/]+)/package_profile/$', 'ConsumerProfileUpdate',

    '/([^/]+)/(%s)/$' % '|'.join(ConsumerDeferredFields.exposed_fields),
    'ConsumerDeferredFields',

    '/([^/]+)/(%s)/$' % '|'.join(ConsumerActions.exposed_actions),
    'ConsumerActions',
)

application = web.application(URLS, globals())
