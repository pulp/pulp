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

import logging
from datetime import datetime
from gettext import gettext as _

import web

from pulp.common import dateutils
from pulp.server import async
from pulp.server.api.consumer_group import ConsumerGroupApi
from pulp.server.api.consumer import ConsumerApi
from pulp.server.auth.authorization import (CREATE, READ, UPDATE, DELETE,
    EXECUTE, grant_automatic_permissions_for_created_resource)
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import (
    auth_required, error_handler)
from pulp.server.webservices.http import extend_uri_path, resource_path
from pulp.server.tasking.scheduler import AtScheduler

# consumers api ---------------------------------------------------------------

api = ConsumerGroupApi()
log = logging.getLogger('pulp')

# controllers -----------------------------------------------------------------

class ConsumerGroups(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self):
        """
        List all available consumergroups.
        @return: a list of all consumergroups
        """
        # implement filters
        return self.ok(api.consumergroups())

    @error_handler
    @auth_required(CREATE)
    def POST(self):
        """
        Create a new consumer group.
        @return: consumer group metadata on successful creation
        """
        consumergroup_data = self.params()
        if api.consumergroup(consumergroup_data['id']) is not None:
            return self.conflict('A consumer group with the id, %s, already exists' % consumergroup_data['id'])
        consumergroup = api.create(consumergroup_data['id'], consumergroup_data['description'],
                                   consumergroup_data['consumerids'])
        resource = resource_path(extend_uri_path(consumergroup['id']))
        grant_automatic_permissions_for_created_resource(resource)
        return self.created(consumergroup['id'], consumergroup)

    def PUT(self):
        log.debug('deprecated ConsumerGroups.PUT method called')
        return self.POST()

    @error_handler
    @auth_required(DELETE)
    def DELETE(self):
        """
        @return: True on successful deletion of all consumer groups
        """
        api.clean()
        return self.ok(True)


class ConsumerGroup(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self, id):
        """
        Get a consumergroup's meta data.
        @param id: consumer group id
        @return: consumer group meta data
        """
        return self.ok(api.consumergroup(id))

    @error_handler
    @auth_required(UPDATE)
    def PUT(self, id):
        """
        Update consumer group
        @param id: The consumer group id
        """
        delta = self.params()
        consumergroup = api.update(id, delta)
        return self.ok(True)

    @error_handler
    @auth_required(DELETE)
    def DELETE(self, id):
        """
        Delete a consumer group.
        @param id: consumer group id
        @return: True on successful deletion of consumer
        """
        if api.consumergroup(id) is None:
            return self.not_found("A consumer group with id, %s, does not exist" % id)
        api.delete(id=id)
        return self.ok(True)

class ConsumerGroupActions(JSONController):

    # See pulp.webservices.repositories.RepositoryActions for design

    exposed_actions = (
        'bind',
        'unbind',
        'add_key_value_pair',
        'delete_key_value_pair',
        'update_key_value_pair',
        'add_consumer',
        'delete_consumer',
        'installpackages',
        'updatepackages',
        'uninstallpackages',
        'installpackagegroups',
        'uninstallpackagegroups',
        'installerrata',
    )

    def validate_consumergroup(self, id):
        if not api.consumergroup(id):
            return False
        else:
            return True

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
        return self.ok(True)

    def add_key_value_pair(self, id):
        """
        Add key-value information to consumergroup.
        @param id: consumergroup id
        """
        data = self.params()
        api.add_key_value_pair(id, data['key'], data['value'], data['force'])
        return self.ok(True)

    def delete_key_value_pair(self, id):
        """
        Delete key-value information from consumergroup.
        @param id: consumergroup id
        """
        data = self.params()
        api.delete_key_value_pair(id, data)
        return self.ok(True)

    def update_key_value_pair(self, id):
        """
        Update key-value information of a consumergroup.
        @param id: consumergroup id
        """
        data = self.params()
        api.update_key_value_pair(id, data['key'], data['value'])
        return self.ok(True)

    def add_consumer(self, id):
        """
        Add a consumer to the group.
        @param id: consumer group id
        """
        data = self.params()
        consumerApi = ConsumerApi()
        if consumerApi.consumer(data) is None:
            return self.not_found('Consumer [%s] does not exist' % data)
        api.add_consumer(id, data)
        return self.ok(True)

    def delete_consumer(self, id):
        """
        Delete a consumer from the group.
        @param id: consumer group id
        """
        data = self.params()
        consumerApi = ConsumerApi()
        if consumerApi.consumer(data) is None:
            return self.not_found('Consumer [%s] does not exist' % data)
        api.delete_consumer(id, data)
        return self.ok(None)

    def installpackages(self, id):
        """
        Install packages.
        Body contains a list of package names.
        """
        data = self.params()
        names = data.get('packagenames', [])
        job = api.installpackages(id, names)
        scheduled_time = data.get('scheduled_time', None)
        for task in job.tasks:
            if scheduled_time is not None:
                dt = dateutils.parse_iso8601_datetime(scheduled_time)
                dt = dateutils.to_utc_datetime(dt)
                task.scheduler = AtScheduler(dt)
            async.enqueue(task, unique=False)
        jobdict = self._job_to_dict(job)
        return self.ok(jobdict)

    def updatepackages(self, id):
        """
        Install packages.
        Body contains a list of package names.
        """
        data = self.params()
        names = data.get('packagenames', [])
        job = api.updatepackages(id, names)
        scheduled_time = data.get('scheduled_time', None)
        for task in job.tasks:
            if scheduled_time is not None:
                dt = dateutils.parse_iso8601_datetime(scheduled_time)
                dt = dateutils.to_utc_datetime(dt)
                task.scheduler = AtScheduler(dt)
            async.enqueue(task, unique=False)
        jobdict = self._job_to_dict(job)
        return self.ok(jobdict)

    def uninstallpackages(self, id):
        """
        Uninstall packages.
        Body contains a list of package names.
        """
        data = self.params()
        names = data.get('packagenames', [])
        job = api.uninstallpackages(id, names)
        scheduled_time = data.get('scheduled_time', None)
        for task in job.tasks:
            if scheduled_time is not None:
                dt = dateutils.parse_iso8601_datetime(scheduled_time)
                dt = dateutils.to_utc_datetime(dt)
                task.scheduler = AtScheduler(dt)
            async.enqueue(task, unique=False)
        jobdict = self._job_to_dict(job)
        return self.ok(jobdict)

    def installpackagegroups(self, id):
        """
        Install package groups.
        Body contains a list of package group names.
        """
        data = self.params()
        grpids = data.get('grpids', [])
        job = api.installpackagegroups(id, grpids)
        scheduled_time = data.get('scheduled_time', None)
        for task in job.tasks:
            if scheduled_time is not None:
                dt = dateutils.parse_iso8601_datetime(scheduled_time)
                dt = dateutils.to_utc_datetime(dt)
                task.scheduler = AtScheduler(dt)
            async.enqueue(task, unique=False)
        jobdict = self._job_to_dict(job)
        return self.ok(jobdict)

    def uninstallpackagegroups(self, id):
        """
        Uninstall package groups.
        Body contains a list of package group names.
        """
        data = self.params()
        grpids = data.get('grpids', [])
        job = api.uninstallpackagegroups(id, grpids)
        scheduled_time = data.get('scheduled_time', None)
        for task in job.tasks:
            if scheduled_time is not None:
                dt = dateutils.parse_iso8601_datetime(scheduled_time)
                dt = dateutils.to_utc_datetime(dt)
                task.scheduler = AtScheduler(dt)
            async.enqueue(task, unique=False)
        jobdict = self._job_to_dict(job)
        return self.ok(jobdict)

    def installerrata(self, id):
        """
         Install applicable errata
         Body contains a list of consumer groups
        """
        data = self.params()
        errataids = data.get('errataids', [])
        types = data.get('types', [])
        importkeys = data.get('importkeys', False)
        job = api.installerrata(id, errataids, types=types, importkeys=importkeys)
        if not job:
            return self.not_found('Errata %s you requested are not applicable for this consumergroup' % errataids)
        for task in job.tasks:
            scheduled_time = data.get('scheduled_time', None)
            if scheduled_time is not None:
                dt = dateutils.parse_iso8601_datetime(scheduled_time)
                dt = dateutils.to_utc_datetime(dt)
                task.scheduler = AtScheduler(dt)
            async.enqueue(task, unique=False)
        jobdict = self._job_to_dict(job)
        return self.ok(jobdict)

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
        if action is None:
            return self.internal_server_error('No implementation for %s found' % action_name)
        if not self.validate_consumergroup(id):
            return self.not_found('Consumer Group [%s] does not exist' % id)
        return action(id)


# web.py application ----------------------------------------------------------

URLS = (
    '/$', 'ConsumerGroups',
    '/([^/]+)/$', 'ConsumerGroup',
    '/([^/]+)/(%s)/$' % '|'.join(ConsumerGroupActions.exposed_actions),
    'ConsumerGroupActions',
)

application = web.application(URLS, globals())
