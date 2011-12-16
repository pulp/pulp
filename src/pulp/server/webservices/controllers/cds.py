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

# Python
import logging
from datetime import datetime
from gettext import gettext as _

# 3rd Party
import web

# Pulp
from pulp.common import dateutils
from pulp.server import async
from pulp.server.api import scheduled_sync
from pulp.server.api import task_history
from pulp.server.api.cds import CdsApi
import pulp.server.api.cds_history as cds_history
from pulp.server.api.cds_history import CdsHistoryApi
from pulp.server.auth.authorization import (CREATE, READ, DELETE, EXECUTE, UPDATE,
    grant_automatic_permissions_for_created_resource)
from pulp.server.webservices import http
from pulp.server.webservices import validation
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import (
    auth_required, error_handler)
from pulp.server.agent import CdsAgent


# globals ---------------------------------------------------------------------

cds_api = CdsApi()
cds_history_api = CdsHistoryApi()
log = logging.getLogger(__name__)

# restful controllers ---------------------------------------------------------

class CdsInstances(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self):
        cds_instances = cds_api.list()
        # inject heartbeat info
        for cds in cds_instances:
            uuid = CdsAgent.uuid(cds)
            heartbeat = CdsAgent.status([uuid,])
            cds['heartbeat'] = heartbeat.values()[0]
        return self.ok(cds_instances)

    @error_handler
    @auth_required(CREATE)
    def POST(self):
        repo_data = self.params()
        hostname = repo_data['hostname']

        existing = cds_api.cds(hostname)
        if existing is not None:
            return self.conflict('A CDS with the hostname [%s] already exists' % hostname)

        name = repo_data.get('name', None)
        description = repo_data.get('description', None)
        sync_schedule = repo_data.get('sync_schedule', None)
        cluster_id = repo_data.get('cluster_id', None)

        cds = cds_api.register(hostname, name, description, sync_schedule=sync_schedule, cluster_id=cluster_id)

        path = http.extend_uri_path(hostname)
        grant_automatic_permissions_for_created_resource(http.resource_path(path))
        return self.created(path, cds)

    def PUT(self):
        log.debug('deprecated CdsInstances.PUT method called')
        return self.POST()


class CdsInstance(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self, id):
        cds = cds_api.cds(id)
        if cds is None:
            return self.not_found('Could not find CDS with hostname [%s]' % id)

        # Inject heartbeat info
        uuid = CdsAgent.uuid(cds)
        heartbeat = CdsAgent.status([uuid,])
        cds['heartbeat'] = heartbeat.values()[0]

        # Inject task info
        cds['next_scheduled_sync'] = None
        task = scheduled_sync.find_scheduled_task(id, 'cds_sync')
        if task and task.scheduled_time is not None:
            cds['next_scheduled_sync'] = dateutils.format_iso8601_datetime(task.scheduled_time)

        return self.ok(cds)

    @error_handler
    @auth_required(UPDATE)
    def PUT(self, id):
        """
        [[wiki]]
        title: Update a CDS instance
        description: Change an exisiting CDS instance.
        method: PUT
        path: /cds/<id>/
        permission: UPDATE
        success response: 200 OK
        return: a CDS object
        parameters: mapping of property to value to change; valid changes: name, description, sync_schedule, cluster_id
        """
        delta = self.params()
        updated = cds_api.update(id, delta)
        return self.ok(updated)

    @error_handler
    @auth_required(DELETE)
    def DELETE(self, id):
        data = self.params()

        force = False
        if 'force' in data:
            force = bool(data['force'])

        cds_api.unregister(id, force=force)
        return self.ok(True)


class CdsActions(JSONController):

    exposed_actions = (
        'associate',
        'unassociate',
        'history',
    )

    def associate(self, id):
        data = self.params()
        repo_id = data.get('repo_id')
        cds_api.associate_repo(id, repo_id)

        # Kick off the async task
        task = async.run_async(cds_api.redistribute, [repo_id], unique=True)

        # If no task was returned, the uniqueness check was tripped which means
        # there's already a redistribute running for the given repo
        if task is None:
            return self.conflict('Sync already in process for repo [%s]' % repo_id)

        # Munge the task information to return to the caller
        task_info = self._task_to_dict(task)
        return self.accepted(task_info)

    def unassociate(self, id):
        data = self.params()
        repo_id = data.get('repo_id')
        cds_api.unassociate_repo(id, repo_id)

        # Kick off the async task
        task = async.run_async(cds_api.redistribute, [repo_id], unique=True)

        # If no task was returned, the uniqueness check was tripped which means
        # there's already a redistribute running for the given repo
        if task is None:
            return self.conflict('Sync already in process for repo [%s]' % repo_id)

        # Munge the task information to return to the caller
        task_info = self._task_to_dict(task)
        return self.accepted(task_info)

    def history(self, id):
        data = self.params()

        event_type = data.get('event_type', None)
        limit = data.get('limit', None)
        sort = data.get('sort', None)
        start_date = data.get('start_date', None)
        end_date = data.get('end_date', None)

        if sort is None:
            sort = cds_history.SORT_DESCENDING

        if limit:
            limit = int(limit)

        if start_date:
            d = dateutils.parse_iso8601_date(start_date)
            start_date = datetime(year=d.year, month=d.month, day=d.day,
                                  tzinfo=dateutils.local_tz())

        if end_date:
            d = dateutils.parse_iso8601_date(end_date)
            end_date = datetime(year=d.year, month=d.month, day=d.day,
                                tzinfo=dateutils.local_tz())

        results = cds_history_api.query(cds_hostname=id, event_type=event_type, limit=limit,
                                        sort=sort, start_date=start_date, end_date=end_date)
        return self.ok(results)

    @error_handler
    @auth_required(EXECUTE)
    def POST(self, id, action_name):
        '''
        Action dispatcher. This method checks to see if the action is exposed,
        and if so, implemented. It then calls the corresponding method (named
        the same as the action) to handle the request.

        @param id: CDS hostname
        @type  id: string

        @param action_name: name of the action to invoke
        @type  action_name: string

        @return: http response
        '''
        cds = cds_api.cds(id)
        if not cds:
            return self.not_found('No CDS with hostname [%s] found' % id)
        action = getattr(self, action_name, None)
        if action is None:
            return self.internal_server_error('No implementation for [%s] found' % action_name)
        return action(id)

class CdsSyncActions(JSONController):

    @error_handler
    @auth_required(EXECUTE)
    def POST(self, id):
        '''
        Triggers a sync against the CDS identified by id.
        '''

        cds = cds_api.cds(id)
        if cds is None:
            return self.not_found('Could not find CDS with hostname [%s]' % id)

        # Check to see if a timeout was specified
        params = self.params()
        timeout = None
        try:
            if 'timeout' in params:
                timeout = validation.timeout.iso8601_duration_to_timeout(params['timeout'])
        except validation.timeout.UnsupportedTimeoutInterval, e:
            return self.bad_request(msg=e.args[0])

        # Kick off the async task
        task = async.run_async(cds_api.cds_sync, [id], timeout=timeout, unique=True)

        # If no task was returned, the uniqueness check was tripped which means
        # there's already a sync running for this CDS.
        if task is None:
            return self.conflict('Sync already in process for CDS [%s]' % id)

        # Munge the task information to return to the caller
        task_info = self._task_to_dict(task)
        return self.accepted(task_info)

    @error_handler
    @auth_required(READ)
    def GET(self, id):
        '''
        Returns a list of tasks associated with the CDS identified by id.
        '''

        # Find all sync tasks associated with the given CDS
        tasks = [t for t in async.find_async(method_name='cds_sync')
                 if id in t.args]

        if len(tasks) == 0:
            return self.not_found('No sync tasks found for CDS [%s]' % id)

        all_task_infos = []
        for task in tasks:
            info = self._task_to_dict(task)
            all_task_infos.append(info)

        return self.ok(all_task_infos)


class CDSTaskHistory(JSONController):

    available_histories = (
        'sync',
    )

    def sync(self, hostname):
        return self.ok(task_history.cds_sync(hostname))

    def GET(self, hostname, action):
        """
        [wiki]
        title: CDS Action History
        description: List completed actions and their retults for a CDS instance.
        method: GET
        path: /cds/<hostname>/history/<action name>/
        permission: READ
        success response: 200 OK
        failure response: 404 Not Found if the CDS instance does not exist or no action information is available
        return: list of task history object
        """
        cds = cds_api.cds(hostname)
        if not cds:
            return self.not_found('No CDS with hostname [%s] found' % hostname)
        method = getattr(self, action, None)
        if method is None:
            return self.not_found(_('No history available for %s on %s') %
                                  (action, hostname))
        return method(hostname)

# web.py application ----------------------------------------------------------

urls = (
    '/$', 'CdsInstances',
    '/([^/]+)/(%s)/$' % '|'.join(CdsActions.exposed_actions), 'CdsActions',
    '/([^/]+)/sync/$', 'CdsSyncActions',
    '/([^/]+)/$', 'CdsInstance',

    '/([^/]+)/history/(%s)/$' % '|'.join(CDSTaskHistory.available_histories),
    'CDSTaskHistory',
)

application = web.application(urls, globals())
