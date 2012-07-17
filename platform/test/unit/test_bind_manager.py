#!/usr/bin/python
#
# Copyright (c) 2012 Red Hat, Inc.
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

import mock

import base
import mock_plugins
import pulp.plugins.loader as plugin_loader
from pulp.server.db.model.consumer import Consumer, Bind
from pulp.server.db.model.repository import Repo, RepoDistributor
from pulp.server.exceptions import MissingResource
from pulp.server.managers import factory

# -- test cases ---------------------------------------------------------------

class BindManagerTests(base.PulpAsyncServerTests):

    CONSUMER_ID = 'test-consumer'
    REPO_ID = 'test-repo'
    DISTRIBUTOR_ID = 'test-distributor'
    QUERY = dict(
        consumer_id=CONSUMER_ID,
        repo_id=REPO_ID,
        distributor_id=DISTRIBUTOR_ID,
        )

    def setUp(self):
        super(BindManagerTests, self).setUp()
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        plugin_loader._create_loader()
        mock_plugins.install()

    def tearDown(self):
        super(BindManagerTests, self).tearDown()
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

    def test_bind(self):
        # Setup
        self.populate()
        # Test
        manager = factory.consumer_bind_manager()
        manager.bind(
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID)
        # Verify
        collection = Bind.get_collection()
        bind = collection.find_one(self.QUERY)
        self.assertTrue(bind is not None)
        self.assertEquals(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEquals(bind['repo_id'], self.REPO_ID)
        self.assertEquals(bind['distributor_id'], self.DISTRIBUTOR_ID)

    def test_unbind(self):
        # Setup
        self.test_bind()
        # Test
        manager = factory.consumer_bind_manager()
        manager.unbind(
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID)
        # Verify
        collection = Bind.get_collection()
        bind = collection.find_one(self.QUERY)
        self.assertTrue(bind is None)

    def test_get_bind(self):
        # Setup
        self.test_bind()
        manager = factory.consumer_bind_manager()
        # Test
        bind = manager.get_bind(
            self.CONSUMER_ID,
            self.REPO_ID,
            self.DISTRIBUTOR_ID)
        # Verify
        self.assertTrue(bind is not None)
        self.assertEquals(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEquals(bind['repo_id'], self.REPO_ID)
        self.assertEquals(bind['distributor_id'], self.DISTRIBUTOR_ID)

    def test_find_all(self):
        # Setup
        self.test_bind()
        manager = factory.consumer_bind_manager()
        # Test
        binds = manager.find_all()
        # Verify
        self.assertEquals(len(binds), 1)
        bind = binds[0]
        self.assertEquals(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEquals(bind['repo_id'], self.REPO_ID)
        self.assertEquals(bind['distributor_id'], self.DISTRIBUTOR_ID)

    def test_find_by_consumer(self):
        # Setup
        self.test_bind()
        manager = factory.consumer_bind_manager()
        # Test
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        # Verify
        self.assertEquals(len(binds), 1)
        bind = binds[0]
        self.assertEquals(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEquals(bind['repo_id'], self.REPO_ID)
        self.assertEquals(bind['distributor_id'], self.DISTRIBUTOR_ID)

    @mock.patch.object(Bind, 'get_collection')
    def test_find_by_consumer_list(self, mock_get_collection):
        manager = factory.consumer_bind_manager()
        CONSUMER_IDS = ['consumer1', 'consumer2']
        mock_collection = mock_get_collection.return_value
        # return a fake binding list
        mock_collection.find.return_value = [
            {'id' : 'binding1', 'consumer_id' : 'consumer1'}
        ]

        ret = manager.find_by_consumer_list(CONSUMER_IDS)

        mock_collection.find.assert_called_once_with(
            {'consumer_id': {'$in': CONSUMER_IDS}})

        self.assertTrue(isinstance(ret, dict))
        self.assertTrue('consumer1' in ret)
        self.assertEqual(ret['consumer1'][0]['id'], 'binding1')

    def test_find_by_repo(self):
        # Setup
        self.test_bind()
        manager = factory.consumer_bind_manager()
        # Test
        binds = manager.find_by_repo(self.REPO_ID)
        # Verify
        self.assertEquals(len(binds), 1)
        bind = binds[0]
        self.assertEquals(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEquals(bind['repo_id'], self.REPO_ID)
        self.assertEquals(bind['distributor_id'], self.DISTRIBUTOR_ID)

    def test_find_by_distributor(self):
        # Setup
        self.test_bind()
        manager = factory.consumer_bind_manager()
        # Test
        binds = manager.find_by_distributor(self.REPO_ID, self.DISTRIBUTOR_ID)
        # Verify
        self.assertEquals(len(binds), 1)
        bind = binds[0]
        self.assertEquals(bind['consumer_id'], self.CONSUMER_ID)
        self.assertEquals(bind['repo_id'], self.REPO_ID)
        self.assertEquals(bind['distributor_id'], self.DISTRIBUTOR_ID)

    def test_consumer_deleted(self):
        # Setup
        self.test_bind()
        manager = factory.consumer_bind_manager()
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        self.assertEquals(len(binds), 1)
        # Test
        manager.consumer_deleted(self.CONSUMER_ID)
        # Verify
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        self.assertEquals(len(binds), 0)

    def test_repo_deleted(self):
        # Setup
        self.test_bind()
        manager = factory.consumer_bind_manager()
        binds = manager.find_by_repo(self.REPO_ID)
        self.assertEquals(len(binds), 1)
        # Test
        manager.repo_deleted(self.REPO_ID)
        # Verify
        binds = manager.find_by_repo(self.REPO_ID)
        self.assertEquals(len(binds), 0)

    def test_distributor_deleted(self):
        # Setup
        self.test_bind()
        manager = factory.consumer_bind_manager()
        binds = manager.find_by_distributor(self.REPO_ID, self.DISTRIBUTOR_ID)
        self.assertEquals(len(binds), 1)
        # Test
        manager.distributor_deleted(self.REPO_ID, self.DISTRIBUTOR_ID)
        # Verify
        binds = manager.find_by_distributor(self.REPO_ID, self.DISTRIBUTOR_ID)
        self.assertEquals(len(binds), 0)

    def test_consumer_unregister_cleanup(self):
        # Setup
        self.test_bind()
        manager = factory.consumer_bind_manager()
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        self.assertEquals(len(binds), 1)
        # Test
        manager = factory.consumer_manager()
        manager.unregister(self.CONSUMER_ID)
        # Verify
        manager = factory.consumer_bind_manager()
        binds = manager.find_by_consumer(self.CONSUMER_ID)
        self.assertEquals(len(binds), 0)

    def test_remove_repo_cleanup(self):
        # Setup
        self.test_bind()
        manager = factory.consumer_bind_manager()
        binds = manager.find_by_repo(self.REPO_ID)
        self.assertEquals(len(binds), 1)
        # Test
        manager = factory.repo_manager()
        manager.delete_repo(self.REPO_ID)
        # Verify
        manager = factory.consumer_bind_manager()
        binds = manager.find_by_repo(self.REPO_ID)
        self.assertEquals(len(binds), 0)

    def test_remove_distributor_cleanup(self):
        # Setup
        self.test_bind()
        manager = factory.consumer_bind_manager()
        binds = manager.find_by_distributor(self.REPO_ID, self.DISTRIBUTOR_ID)
        self.assertEquals(len(binds), 1)
        # Test
        manager = factory.repo_distributor_manager()
        manager.remove_distributor(self.REPO_ID, self.DISTRIBUTOR_ID)
        # Verify
        manager = factory.consumer_bind_manager()
        binds = manager.find_by_distributor(self.REPO_ID, self.DISTRIBUTOR_ID)
        self.assertEquals(len(binds), 0)

    #
    # Error Cases
    #

    def test_get_missing_bind(self):
        # Setup
        self.populate()
        manager = factory.consumer_bind_manager()
        # Test
        try:
            manager.get_bind(
                self.CONSUMER_ID,
                self.REPO_ID,
                self.DISTRIBUTOR_ID)
            raise Exception('MissingResource <Bind>, expected')
        except MissingResource:
            # expected
            pass

    def test_bind_missing_consumer(self):
        # Setup
        self.populate()
        collection = Consumer.get_collection()
        collection.remove({})
        # Test
        manager = factory.consumer_bind_manager()
        try:
            manager.bind(
                self.CONSUMER_ID,
                self.REPO_ID,
                self.DISTRIBUTOR_ID)
            raise Exception('MissingResource <Consumer>, expected')
        except MissingResource:
            # expected
            pass
            # Verify
        collection = Bind.get_collection()
        binds = collection.find({})
        binds = [b for b in binds]
        self.assertEquals(len(binds), 0)

    def test_bind_missing_distributor(self):
        # Setup
        self.populate()
        collection = RepoDistributor.get_collection()
        collection.remove({})
        # Test
        manager = factory.consumer_bind_manager()
        try:
            manager.bind(
                self.CONSUMER_ID,
                self.REPO_ID,
                self.DISTRIBUTOR_ID)
            raise Exception('MissingResource <RepoDistributor>, expected')
        except MissingResource:
            # expected
            pass
            # Verify
        collection = Bind.get_collection()
        binds = collection.find({})
        binds = [b for b in binds]
        self.assertEquals(len(binds), 0)
