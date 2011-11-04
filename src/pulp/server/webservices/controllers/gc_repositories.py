#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
from gettext import gettext as _

# 3rd Party
import web

# Pulp
from pulp.server.auth.authorization import CREATE, READ, DELETE, EXECUTE, UPDATE
import pulp.server.managers.factory as manager_factory
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required, error_handler

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- controllers --------------------------------------------------------------

class RepoCreateDelete(JSONController):

    # POST:    Repository Create
    # DELETE:  Repository Delete

    @error_handler
    @auth_required(CREATE)
    def POST(self, id):

        # Pull the repo data out of the request body (validation will occur
        # in the manager)
        repo_data = self.params()
        display_name = repo_data.get('display_name', None)
        description = repo_data.get('description', None)
        notes = repo_data.get('notes', None)

        # Creation
        repo_manager = manager_factory.repo_manager()
        repo_manager.create_repo(id, display_name, description, notes)

        return self.ok(True)

    @error_handler
    @auth_required(DELETE)
    def DELETE(self, id):

        # Parameters
        params = self.params()
        delete_content = params.get('delete_content', True)

        # Deletion
        repo_manager = manager_factory.repo_manager()
        repo_manager.delete_repo(id, delete_content)

        return self.ok(True)

class RepoImporters(JSONController):

    # POST:   Set Importer
    # DELETE: Remove Importer  (currently not supported)

    @error_handler
    @auth_required(CREATE)
    def POST(self, repo_id):

        # Params (validation will occur in the manager)
        params = self.params()
        importer_type = params.get('importer_type_id', None)
        importer_config = params.get('importer_config', None)

        # Update the repo
        repo_manager = manager_factory.repo_manager()
        repo_manager.set_importer(repo_id, importer_type, importer_config)

        return self.ok(True)

class RepoDistributor(JSONController):

    # POST:   Add Distributor

    @error_handler
    @auth_required(CREATE)
    def POST(self, repo_id):

        # Distributor ID is optional and thus isn't part of the URL

        # Params (validation will occur in the manager)
        params = self.params()
        distributor_type = params.get('distributor_type_id', None)
        distributor_config = params.get('distributor_config', None)
        distributor_id = params.get('distributor_id', None)
        auto_publish = params.get('auto_publish', False)

        # Update the repo
        repo_manager = manager_factory.repo_manager()
        repo_manager.add_distributor(repo_id, distributor_type, distributor_config, auto_publish, distributor_id)

        return self.ok(True)

class RepoDistributors(JSONController):

    # DELETE: Remove Distributor

    @error_handler
    @auth_required(DELETE)
    def DELETE(self, repo_id, distributor_id):
        repo_manager = manager_factory.repo_manager()
        repo_manager.remove_distributor(repo_id, distributor_id)

class RepoSync(JSONController):

    # POST:  Trigger a repo sync

    @error_handler
    @auth_required(EXECUTE)
    def POST(self, repo_id):

        # TODO: Add timeout support

        # Params
        params = self.params()
        overrides = params.get('override_config', None)

        # Trigger the sync
        # TODO: Make this run asynchronously
        repo_sync_manager = manager_factory.repo_sync_manager()
        repo_sync_manager.sync(repo_id, overrides)

        return self.ok(True)

class RepoPublish(JSONController):

    # POST:  Trigger a repo publish

    @error_handler
    @auth_required(EXECUTE)
    def POST(self, repo_id, distributor_id):

        # TODO: Add timeout support

        # Params
        params = self.params()
        overrides = params.get('override_config', None)

        # Trigger the publish
        # TODO: Make this run asynchronously
        repo_publish_manager = manager_factory.repo_publish_manager()
        repo_publish_manager.publish(repo_id, distributor_id, overrides)
        
        return self.ok(True)

class ListRepositories(JSONController):

    # This is temporary and will be replaced by a more fleshed out repo query mechanism

    # GET:  Retrieve all repositories in the system

    @error_handler
    @auth_required(READ)
    def GET(self):
        repo_query_manager = manager_factory.repo_query_manager()
        all_repos = repo_query_manager.find_all()
        return self.ok(all_repos)

# -- web.py application -------------------------------------------------------

urls = (
    '/', 'ListRepositories',
    '/([^/]+)/$', 'RepoCreateDelete',
    '/([^/]+)/importers/$', 'RepoImporters',
    '/([^/]+)/distributors/$', 'RepoDistributor',
    '/([^/]+)/distributors/([^/]+)/$', 'RepoDistributors',
    '/([^/]+)/sync/$', 'RepoSync',
    '/([^/]+)/publish/([^/]+)/$', 'RepoPublish',
)

application = web.application(urls, globals())
