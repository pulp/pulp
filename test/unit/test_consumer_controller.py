#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
import sys

import mock

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

import mock_plugins
import pulp.server.content.loader as plugin_loader
from pulp.server.managers import factory
from pulp.server.db.model.gc_consumer import Consumer, Bind
from pulp.server.db.model.gc_repository import Repo, RepoDistributor
from pulp.server.webservices.controllers import statuses

class BindTest(testutil.PulpV2WebserviceTest):
    
    CONSUMER_ID = 'mycon'
    REPO_ID = 'myrepo'
    DISTRIBUTOR_ID = 'mydist'
    QUERY = dict(
        consumer_id=CONSUMER_ID,
        repo_id=REPO_ID,
        distributor_id=DISTRIBUTOR_ID,
    )

    def setUp(self):
        testutil.PulpV2WebserviceTest.setUp(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        plugin_loader._create_loader()
        mock_plugins.install()
        
    def tearDown(self):
        testutil.PulpTest.tearDown(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        mock_plugins.reset()
    
    def populate(self):
        config = {'key1' : 'value1', 'key2' : None}
        manager = factory.repo_manager()
        repo = manager.create_repo(self.REPO_ID)
        manager = factory.repo_distributor_manager()
        manager.add_distributor(
            self.REPO_ID,
            'mock-distributor',
            config,
            True,
            distributor_id=self.DISTRIBUTOR_ID)
        manager = factory.consumer_manager()
        manager.register(self.CONSUMER_ID)
        
    def test_bind(self):
        # Setup
        self.populate()
        # Test
        path = '/v2/consumers/%s/bindings/' % self.CONSUMER_ID
        body = dict(
            repo_id=self.REPO_ID,
            distributor_id=self.DISTRIBUTOR_ID,)
        status, body = self.post(path, body)
        # Verify
        manager = factory.consumer_bind_manager()
        self.assertEquals(status, 200)
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        binds = [b for b in binds]
        self.assertEquals(len(binds), 1)
        bind = binds[0]
        for k in ('consumer_id', 'repo_id', 'distributor_id'):
            self.assertEquals(bind[k], body[k])
