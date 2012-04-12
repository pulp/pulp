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
import mockagent

import pulp.server.content.loader as plugin_loader
from pulp.server.managers import factory
from pulp.server.db.model.gc_consumer import Consumer, Bind
from pulp.server.db.model.gc_repository import Repo, RepoDistributor
from pulp.server.webservices.controllers import statuses


class BindTest(testutil.PulpV2WebserviceTest):
    
    CONSUMER_ID = 'test-consumer'
    REPO_ID = 'test-repo'
    DISTRIBUTOR_ID = 'test-distributor'
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
        Bind.get_collection().remove()
        plugin_loader._create_loader()
        mock_plugins.install()
        mockagent.install()
        
    def tearDown(self):
        testutil.PulpTest.tearDown(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
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
        
    def test_get_bind(self):
        # Setup
        self.populate()
        # Test
        manager = factory.consumer_bind_manager()
        bind = manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        # Test
        path = '/v2/consumers/%s/bindings/%s/%s/' % \
            (self.CONSUMER_ID,
             self.REPO_ID,
             self.DISTRIBUTOR_ID)
        status, body = self.get(path)
        self.assertEquals(status, 200)
        self.assertTrue(body is not None)
        self.assertEquals(body['consumer_id'], self.CONSUMER_ID)
        self.assertEquals(body['repo_id'], self.REPO_ID)
        self.assertEquals(body['distributor_id'], self.DISTRIBUTOR_ID)
        self.assertTrue('_href' in body)

    def test_get_bind_by_consumer(self):
        # Setup
        self.populate()
        # Test
        manager = factory.consumer_bind_manager()
        bind = manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        # Test
        path = '/v2/consumers/%s/bindings/' % self.CONSUMER_ID
        status, body = self.get(path)
        self.assertEquals(status, 200)
        self.assertEquals(len(body), 1)
        bind = body[0]
        self.assertEquals(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEquals(bind['repo_id'], self.REPO_ID)
        self.assertEquals(bind['distributor_id'], self.DISTRIBUTOR_ID)
        self.assertTrue('_href' in bind)
        manager = factory.repo_distributor_manager()
        distributor = manager.get_distributor(self.REPO_ID, self.DISTRIBUTOR_ID)
        for k in ('distributor_type_id', 'config'):
            self.assertEquals(
                bind['distributor'][k],
                distributor[k])

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
        self.assertEquals(status, 201)
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        self.assertEquals(len(binds), 1)
        bind = binds[0]
        for k in ('consumer_id', 'repo_id', 'distributor_id'):
            self.assertEquals(bind[k], body[k])

    def test_unbind(self):
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        bind = manager.bind(self.CONSUMER_ID, self.REPO_ID, self.DISTRIBUTOR_ID)
        # Test
        path = '/v2/consumers/%s/bindings/%s/%s/' % \
            (self.CONSUMER_ID,
             self.REPO_ID,
             self.DISTRIBUTOR_ID)
        status, body = self.delete(path)
        # Verify
        self.assertEquals(status, 200)
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        self.assertEquals(len(binds), 0)

    #
    # Failure Cases
    #

    def test_bind_missing_consumer(self):
        # Setup
        self.populate()
        collection = Consumer.get_collection()
        collection.remove({})
        # Test
        path = '/v2/consumers/%s/bindings/' % self.CONSUMER_ID
        body = dict(
            repo_id=self.REPO_ID,
            distributor_id=self.DISTRIBUTOR_ID,)
        status, body = self.post(path, body)
        # Verify
        manager = factory.consumer_bind_manager()
        self.assertEquals(status, 404)
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        print binds
        self.assertEquals(len(binds), 0)
        
    def test_bind_missing_distributor(self):
        # Setup
        self.populate()
        collection = RepoDistributor.get_collection()
        collection.remove({})
        # Test
        path = '/v2/consumers/%s/bindings/' % self.CONSUMER_ID
        body = dict(
            repo_id=self.REPO_ID,
            distributor_id=self.DISTRIBUTOR_ID,)
        status, body = self.post(path, body)
        # Verify
        manager = factory.consumer_bind_manager()
        self.assertEquals(status, 404)
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        self.assertEquals(len(binds), 0)


class ContentTest(testutil.PulpV2WebserviceTest):

    CONSUMER_ID = 'test-consumer'
    REPO_ID = 'test-repo'
    DISTRIBUTOR_ID = 'test-distributor'

    def setUp(self):
        testutil.PulpV2WebserviceTest.setUp(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        plugin_loader._create_loader()
        mock_plugins.install()
        mockagent.install()

    def tearDown(self):
        testutil.PulpTest.tearDown(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
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

    def test_install(self):
        # Setup
        self.populate()
        # Test
        md = dict(name='python-gofer', version='0.66')
        unit = dict(type_id='rpm', metadata=md)
        units = [unit,]
        options = dict(importkeys=True)
        path = '/v2/consumers/%s/actions/content/install/' % self.CONSUMER_ID
        body = dict(
            units=units,
            options=options,)
        status, body = self.post(path, body)
        # Verify
        self.assertEquals(status, 200) # TODO: 202 when asynchronous

    def test_update(self):
        # Setup
        self.populate()
        # Test
        md = dict(name='gofer', version='0.66')
        unit = dict(type_id='rpm', metadata=md)
        units = [unit,]
        options = dict(importkeys=True)
        path = '/v2/consumers/%s/actions/content/update/' % self.CONSUMER_ID
        body = dict(
            units=units,
            options=options,)
        status, body = self.post(path, body)
        # Verify
        self.assertEquals(status, 200) # TODO: 202 when asynchronous

    def test_uninstall(self):
        # Setup
        self.populate()
        # Test
        md = dict(name='gofer')
        unit = dict(type_id='rpm', metadata=md)
        units = [unit,]
        options = dict(importkeys=True)
        path = '/v2/consumers/%s/actions/content/uninstall/' % self.CONSUMER_ID
        body = dict(
            units=units,
            options=options,)
        status, body = self.post(path, body)
        # Verify
        self.assertEquals(status, 200) # TODO: 202 when asynchronous