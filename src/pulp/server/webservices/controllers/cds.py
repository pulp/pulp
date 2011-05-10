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

# Python
import logging

# 3rd Party
import web

# Pulp
from pulp.common import dateutils
from pulp.server.api import scheduled_sync
from pulp.server.api.cds import CdsApi
import pulp.server.api.cds_history as cds_history
from pulp.server.api.cds_history import CdsHistoryApi
from pulp.server.async import find_async
from pulp.server.auth.authorization import (CREATE, READ, DELETE, EXECUTE,
    grant_automatic_permissions_for_created_resource)
from pulp.server.webservices import http
from pulp.server.webservices.controllers.base import JSONController, AsyncController
from pulp.server import agent
from pulp.server.db.model.cds import CDS


# globals ---------------------------------------------------------------------

cds_api = CdsApi()
cds_history_api = CdsHistoryApi()
log = logging.getLogger(__name__)

# restful controllers ---------------------------------------------------------

class CdsInstances(JSONController):

    @JSONController.error_handler
    @JSONController.auth_required(READ)
    def GET(self):
        cds_instances = cds_api.list()
        # inject heartbeat info
        for cds in cds_instances:
            uuid = CDS.uuid(cds)
            heartbeat = agent.status([uuid,])
            cds['heartbeat'] = heartbeat.values()[0]
        return self.ok(cds_instances)

    @JSONController.error_handler
    @JSONController.auth_required(CREATE)
    def POST(self):
        repo_data = self.params()
        hostname = repo_data['hostname']

        existing = cds_api.cds(hostname)
        if existing is not None:
            return self.conflict('A CDS with the hostname [%s] already exists' % hostname)

        name = None
        description = None
        sync_schedule = None

        if 'name' in repo_data:
            name = repo_data['name']

        if 'description' in repo_data:
            description = repo_data['description']

        if 'sync_schedule' in repo_data:
            sync_schedule = repo_data['sync_schedule']

        cds = cds_api.register(hostname, name, description, sync_schedule=sync_schedule)

        path = http.extend_uri_path(hostname)
        grant_automatic_permissions_for_created_resource(http.resource_path(path))
        return self.created(path, cds)

    def PUT(self):
        log.debug('deprecated CdsInstances.PUT method called')
        return self.POST()


class CdsInstance(JSONController):

    @JSONController.error_handler
    @JSONController.auth_required(READ)
    def GET(self, id):
        cds = cds_api.cds(id)
        if cds is None:
            return self.not_found('Could not find CDS with hostname [%s]' % id)

        # Inject heartbeat info
        uuid = CDS.uuid(cds)
        heartbeat = agent.status([uuid,])
        cds['heartbeat'] = heartbeat.values()[0]

        # Inject task info
        cds['next_scheduled_sync'] = None
        task = scheduled_sync.find_scheduled_task(id, 'cds_sync')
        if task and task.scheduled_time is not None:
            cds['next_scheduled_sync'] = dateutils.format_iso8601_datetime(task.scheduled_time)

        return self.ok(cds)

    @JSONController.error_handler
    @JSONController.auth_required(DELETE)
    def DELETE(self, id):
        cds_api.unregister(id)
        return self.ok(True)


class CdsActions(AsyncController):

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
        task = self.start_task(cds_api.redistribute, [repo_id], unique=True)

        # If no task was returned, the uniqueness check was tripped which means
        # there's already a redistribute running for the given repo
        if task is None:
            return self.conflict('Sync already in process for repo [%s]' % repo_id)

        # Munge the task information to return to the caller
        task_info = self._task_to_dict(task)
        task_info['status_path'] = self._status_path(task.id)
        return self.accepted(task_info)

    def unassociate(self, id):
        data = self.params()
        repo_id = data.get('repo_id')
        cds_api.unassociate_repo(id, repo_id)

        # Kick off the async task
        task = self.start_task(cds_api.redistribute, [repo_id], unique=True)

        # If no task was returned, the uniqueness check was tripped which means
        # there's already a redistribute running for the given repo
        if task is None:
            return self.conflict('Sync already in process for repo [%s]' % repo_id)

        # Munge the task information to return to the caller
        task_info = self._task_to_dict(task)
        task_info['status_path'] = self._status_path(task.id)
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
            start_date = dateutils.to_local_datetime(start_date)
            start_date = dateutils.format_iso8601_datetime(start_date)

        if end_date:
            end_date = dateutils.to_local_datetime(end_date)
            end_date = dateutils.format_iso8601_datetime(end_date)

        results = cds_history_api.query(cds_hostname=id, event_type=event_type, limit=limit,
                                        sort=sort, start_date=start_date, end_date=end_date)
        return self.ok(results)

    @JSONController.error_handler
    @JSONController.auth_required(EXECUTE)
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

class CdsSyncActions(AsyncController):

    @JSONController.error_handler
    @JSONController.auth_required(EXECUTE)
    def POST(self, id):
        '''
        Triggers a sync against the CDS identified by id.
        '''

        # Check to see if a timeout was specified
        params = self.params()
        timeout = self.timeout(params)

        # Kick off the async task
        task = self.start_task(cds_api.cds_sync, [id], timeout=timeout, unique=True)

        # If no task was returned, the uniqueness check was tripped which means
        # there's already a sync running for this CDS.
        if task is None:
            return self.conflict('Sync already in process for CDS [%s]' % id)

        # Munge the task information to return to the caller
        task_info = self._task_to_dict(task)
        task_info['status_path'] = self._status_path(task.id)
        return self.accepted(task_info)

    @JSONController.error_handler
    @JSONController.auth_required(READ)
    def GET(self, id):
        '''
        Returns a list of tasks associated with the CDS identified by id.
        '''

        # Find all sync tasks associated with the given CDS
        tasks = [t for t in find_async(method_name='cds_sync')
                 if id in t.args]

        if len(tasks) == 0:
            return self.not_found('No sync tasks found for CDS [%s]' % id)

        all_task_infos = []
        for task in tasks:
            info = self._task_to_dict(task)
            info['status_path'] = self._status_path(task.id)
            all_task_infos.append(info)

        return self.ok(all_task_infos)


class CdsSyncTaskStatus(AsyncController):

    @JSONController.error_handler
    @JSONController.auth_required(READ)
    def GET(self, id, task_id):
        '''
        Returns the state of an individual CDS sync task.
        '''
        task_info = self.task_status(task_id)
        if task_info is None:
            return self.not_found('No sync with id [%s] found' % task_id)
        return self.ok(task_info)

# web.py application ----------------------------------------------------------

urls = (
    '/$', 'CdsInstances',
    '/([^/]+)/(%s)/$' % '|'.join(CdsActions.exposed_actions), 'CdsActions',
    '/([^/]+)/sync/$', 'CdsSyncActions',
    '/([^/]+)/sync/([^/]+)/$', 'CdsSyncTaskStatus',
    '/([^/]+)/$', 'CdsInstance',
)

application = web.application(urls, globals())
