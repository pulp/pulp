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

# web.py application ----------------------------------------------------------

URLS = (
    '/schedules/$', 'Schedules',
    '/$', 'Root',
    '/([^/]+)/$', 'Repository',
    '/([^/]+)/sync/$', 'Sync',
    '/([^/]+)/sync/([^/]+)/$', 'SyncStatus',
    '/([^/]+)/list/$', 'Packages',
    '/([^/]+)/upload/$', 'Upload',
    '/([^/]+)/add_package/$', 'AddPackage',
)

application = web.application(URLS, globals())

# repository api --------------------------------------------------------------

API = RepoApi(CONFIG)

# controllers -----------------------------------------------------------------

class Root(JSONController):
    
    @JSONController.error_handler
    def GET(self):
        """
        List all available repositories.
        @return: a list of all available repositories
        """
        return self.ok(API.repositories())
    
    @JSONController.error_handler
    def PUT(self):
        """
        Create a new repository.
        @return: repository meta data on successful creation of repository
        """
        repo_data = self.input()
        repo = API.create(repo_data['id'],
                          repo_data['name'],
                          repo_data['arch'],
                          repo_data['feed'],
                          sync_schedule=repo_data['sync_schedule'])
        # TODO need function to creat path
        path = None
        return self.created(path, repo)

    @JSONController.error_handler
    def DELETE(self):
        """
        @return: True on successful deletion of all repositories
        """
        API.clean()
        return self.ok(None)
    
class Repository(JSONController):
    
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
    def POST(self, id):
        """
        Change a repository.
        @param id: repository id
        @return: True on successful update of repository meta data
        """
        repo_data = self.input()
        repo_data['id'] = id
        API.update(repo_data)
        return self.ok(True)
    
    
class Sync(AsyncController):
    
    @JSONController.error_handler
    def POST(self, id):
        """
        Sync a repository from it's feed.
        @param id: repository id
        @return: True on successful sync of repository from feed
        """
        task_info = self.start_task(API.sync, id)
        return self.accepted(task_info)
    
    
class SyncStatus(AsyncController):
    
    @JSONController.error_handler
    def GET(self, id, task_id):
        """
        Check the status of a sync operation.
        @param id: repository id
        @param task_id: sync operation id
        @return: operation status information
        """
        task_info = self.task_status(task_id)
        if task_info is None:
            return self.not_found('No sync with id %s found' % task_id)
        return self.ok(task_info)


class AddPackage(JSONController):
    
    @JSONController.error_handler
    def POST(self, id):
        """
        @param id: repository id
        @return: True on successful addition of package to repository
        """
        data = self.input()
        API.add_package(id, data['packageid'])
        return self.ok(True)
       
  
class Packages(JSONController):
    
    @JSONController.error_handler
    def GET(self, id):
        """
        List all packages in a repository.
        @param id: repository id
        @return: list of all packages available in corresponding repository
        """
        return self.ok(API.packages(id))
    

class Upload(JSONController):

    @JSONController.error_handler
    def POST(self, id):
        """
        Upload a package to a repository.
        @param id: repository id
        @return: True on successful upload
        """
        data = self.input()
        API.upload(data['repo'],
                   data['pkginfo'],
                   data['pkgstream'])
        return self.ok(True)


class Schedules(JSONController):

    @JSONController.error_handler
    def GET(self):
        '''
        Retrieve a map of all repository IDs to their associated synchronization
        schedules.

        @return: key - repository ID, value - synchronization schedule
        '''
        schedules = API.all_schedules()
        return self.ok(schedules)
