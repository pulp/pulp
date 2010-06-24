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

class Repositories(JSONController):
 
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
                          symlinks = repo_data['use_symlinks'],
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
        return self.ok(True)
    

class Repository(JSONController):

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

    @JSONController.error_handler
    def DELETE(self, id):
        """
        Delete a repository.
        @param id: repository id
        @return: True on successful deletion of repository
        """
        API.delete(id=id)
        return self.ok(True)
    

class RepositoryActions(AsyncController):
    
    # All actions have been gathered here into one controller class for both
    # convenience and automatically generate the regular expression that will
    # map valid actions to this class. This also provides a single point for
    # querying existing tasks.
    #
    # There are two steps to implementing a new action:
    # 1. The action name must be added to the tuple of exposed_actions
    # 2. You must add a method to this class with the same name as the action
    #    that takes two positional arguments: 'self' and 'id' where id is the
    #    the repository id. Additional parameters from the body can be
    #    fetched and de-serialized via the self.params() call.
    
    exposed_actions = (
        'list',
        'sync',
        'upload',
        'add_package',
    )

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
       
    def upload(self, id, pkg_data):
        """
        Upload a package to a repository.
        @param id: repository id
        @return: True on successful upload
        """
        data = self.params()
        API.upload(id,
                   data['pkginfo'],
                   data['pkgstream'])
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
        Action dispatcher. This method checks to see if the action is exposed,
        and if so, implemented. It then calls the corresponding method (named
        the same as the action) to handle the request.
        @type id: str
        @param id: repository id
        @type action_name: str
        @param action_name: name of the action
        @return: http response
        """
        action = getattr(self, action_name, None)
        if action is None:
            return self.internal_server_error('No implementation for %s found' % action_name)
        return action(id)
    
    
class RepositoryActionStatus(AsyncController):

    @JSONController.error_handler
    def GET(self, id, action_name, action_id):
        """
        Check the status of a sync operation.
        @param id: repository id
        @param action_name: name of the action
        @param action_id: action id
        @return: action status information
        """
        # XXX there is a bug that re-appends the task id here
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


class Schedules(JSONController):
    
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
 
# web.py application ----------------------------------------------------------

urls = (
    '/$', 'Repositories',
    '/([^/]+)/$', 'Repository',
    '/([^/]+)/(%s)/$' % '|'.join(RepositoryActions.exposed_actions), 'RepositoryActions',
    '/([^/]+)/(%s)/([^/]+)/$' % '|'.join(RepositoryActions.exposed_actions), 'RepositoryActionStatus',
    '/schedules/', 'Schedules',
)

application = web.application(urls, globals())
