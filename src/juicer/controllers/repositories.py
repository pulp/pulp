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

from juicer.controllers.base import JSONController, AsyncController
from juicer.runtime import CONFIG
from pulp.api.repo import RepoApi

# repository api --------------------------------------------------------------

API = RepoApi(CONFIG)

# restful controllers ---------------------------------------------------------

class Collection(JSONController):
 
    @JSONController.error_handler
    def GET(self):
        """
        List all available repositories.
        @return: a list of all available repositories
        """
        # XXX implement filters
        return self.ok(API.repositories())
    
    @JSONController.error_handler
    def PUT(self):
        """
        Create a new repository.
        @return: repository meta data on successful creation of repository
        """
        repo_data = self.params()
        repo = API.create(repo_data['id'],
                          repo_data['name'],
                          repo_data['arch'],
                          repo_data['feed'],
                          sync_schedule=repo_data['sync_schedule'])
        # TODO need function to create path
        path = None
        return self.created(path, repo)

    @JSONController.error_handler
    def DELETE(self):
        """
        @return: True on successful deletion of all repositories
        """
        API.clean()
        return self.ok(None)
    

class CollectionActions(AsyncController):
    actions = (
    )
    

class Object(JSONController):

    @JSONController.error_handler
    def DELETE(self, id):
        """
        Delete a repository.
        @param id: repository id
        @return: True on successful deletion of repository
        """
        API.delete(id=id)
        return self.ok(None)

    @JSONController.error_handler
    def GET(self, id):
        """
        Get information on a single repository.
        @param id: repository id
        @return: repository meta data
        """
        return self.ok(API.repository(id))
    
    @JSONController.error_handler
    def PUT(self, id):
        """
        Change a repository.
        @param id: repository id
        @return: True on successful update of repository meta data
        """
        repo_data = self.params()
        repo_data['id'] = id
        API.update(repo_data)
        return self.ok(True)
    


class ObjectActions(AsyncController):
    actions = (
        'list',
        'sync',
        'upload',
        'add_package',
    )
    
    @JSONController.error_handler
    def GET(self, id, action_name):
        '''
        Retrieve a map of all repository IDs to their associated synchronization
        schedules.

        @return: key - repository ID, value - synchronization schedule
        '''
        # XXX this returns all scheduled tasks, it should only return those
        # tasks that are specified by the action_name
        schedules = API.all_schedules()
        return self.ok(schedules)
 
    def list(self, id):
        """
        List all packages in a repository.
        @param id: repository id
        @return: list of all packages available in corresponding repository
        """
        return self.ok(API.packages(id))
    
    def sync(self, id):
        """
        Sync a repository from it's feed.
        @param id: repository id
        @return: True on successful sync of repository from feed
        """
        task_info = self.start_task(API.sync, id)
        return self.accepted(task_info)
       
    def upload(self, id, repo=None, pkginfo=None, pkgstream=None):
        """
        Upload a package to a repository.
        @param id: repository id
        @return: True on successful upload
        """
        API.upload(repo,
                   pkginfo,
                   pkgstream)
        return self.ok(True)
    
    def add_package(self, id):
        """
        @param id: repository id
        @return: True on successful addition of package to repository
        """
        data = self.params()
        API.add_package(id, data['packageid'])
        return self.ok(True)
    
    @JSONController.error_handler
    def POST(self, id, action_name):
        """
        Object action dispatcher. This method checks to see if the action is
        exposed, and if so, implemented. It then calls the corresponding
        method (named the same as the action) to handle the request.
        @type id: str
        @param id: repository id
        @type action_name: str
        @param action_name: name of the action
        @return: http response
        """
        if action_name not in self.actions:
            return self.not_found('The action %s is not defined' % action_name)
        action = getattr(self, action_name, None)
        if action is None:
            return self.internal_server_error('No implementation for %s found' % action_name)
        params = self.params()
        return action(self, id, **params)
    
    
class ObjectActionStatus(AsyncController):
    
    @JSONController.error_handler
    def GET(self, id, action_name, action_id):
        """
        Check the status of a sync operation.
        @param id: repository id
        @param action_name: name of the action
        @param action_id: action id
        @return: action status information
        """
        task_info = self.task_status(action_id)
        if task_info is None:
            return self.not_found('No %s with id %s found' % (action_name, action_id))
        return self.ok(task_info)
    
    @JSONController.error_handler
    def DELETE(self, id, action_name, action_id):
        """
        Place holder to cancel an action
        """
        return self.not_found('Action cancellation is not yet implemented')

# web.py application ----------------------------------------------------------

urls = (
    '/$', 'Collection',
    '/(%s)/$' % '|'.join(CollectionActions.actions), 'CollectionActions',
    '/([^/]+)/$', 'Object',
    '/([^/]+)/(%s)/$' % '|'.join(ObjectActions.actions), 'ObjectActions',
    '/([^/]+)/(%s)/([^/]+)/$' % '|'.join(ObjectActions.actions), 'ObjectActionStatus',
)

application = web.application(urls, globals())
