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

# Python
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")

import testutil
import mock_plugins

import pulp.server.content.loader as plugin_loader
from pulp.server.db.model.gc_consumer import Consumer, Bind
from pulp.server.db.model.gc_repository import Repo, RepoDistributor
from pulp.server.exceptions import MissingResource
import pulp.server.managers.consumer.cud as consumer_manager
import pulp.server.managers.factory as factory
import pulp.server.exceptions as exceptions

# -- test cases ---------------------------------------------------------------

class ConsumerManagerTests(testutil.PulpTest):

    def setUp(self):
        testutil.PulpTest.setUp(self)

        plugin_loader._create_loader()
        mock_plugins.install()

        # Create the manager instance to test
        self.manager = consumer_manager.ConsumerManager()

    def tearDown(self):
        testutil.PulpTest.tearDown(self)
        mock_plugins.reset()

    def clean(self):
        testutil.PulpTest.clean(self)

        Consumer.get_collection().remove()

    def test_create(self):
        """
        Tests creating a consumer with valid data is successful.
        """

        # Setup
        id = 'consumer_1'
        name = 'Consumer 1'
        description = 'Test Consumer 1'
        notes = {'note1' : 'value1'}

        # Test
        created = self.manager.register(id, name, description, notes)

        # Verify
        consumers = list(Consumer.get_collection().find())
        self.assertEqual(1, len(consumers))

        consumer = consumers[0]
        self.assertEqual(id, consumer['id'])
        self.assertEqual(name, consumer['display_name'])
        self.assertEqual(description, consumer['description'])
        self.assertEqual(notes, consumer['notes'])

        self.assertEqual(id, created['id'])
        self.assertEqual(name, created['display_name'])
        self.assertEqual(description, created['description'])
        self.assertEqual(notes, created['notes'])

    def test_create_defaults(self):
        """
        Tests creating a consumer with minimal information (ID) is successful.
        """

        # Test
        self.manager.register('consumer_1')

        # Verify
        consumers = list(Consumer.get_collection().find())
        self.assertEqual(1, len(consumers))
        self.assertEqual('consumer_1', consumers[0]['id'])

        #   Assert the display name is defaulted to the id
        self.assertEqual('consumer_1', consumers[0]['display_name'])

    def test_create_invalid_id(self):
        """
        Tests creating a consumer with an invalid ID raises the correct error.
        """

        # Test
        try:
            self.manager.register('bad id')
            self.fail('Invalid ID did not raise an exception')
        except exceptions.InvalidValue, e:
            self.assertTrue('bad id' in e)
            print(e) # for coverage

    def test_create_duplicate_id(self):
        """
        Tests creating a consumer with an ID already being used by a consumer raises
        the correct error.
        """

        # Setup
        id = 'duplicate'
        self.manager.register(id)

        # Test
        try:
            self.manager.register(id)
            self.fail('Consumer with an existing ID did not raise an exception')
        except exceptions.DuplicateResource, e:
            self.assertTrue(id in e)
            print(e) # for coverage

    def test_create_invalid_notes(self):
        """
        Tests that creating a consumer but passing a non-dict as the notes field
        raises the correct exception.
        """

        # Setup
        id = 'bad-notes'
        notes = 'not a dict'

        # Test
        try:
            self.manager.register(id, notes=notes)
            self.fail('Invalid notes did not cause create to raise an exception')
        except exceptions.InvalidValue, e:
            self.assertTrue(notes in e)
            print(e) # for coverage

    def test_unregister_consumer(self):
        """
        Tests unregistering a consumer under normal circumstances.
        """

        # Setup
        id = 'doomed'
        self.manager.register(id)

        # Test
        self.manager.unregister(id)

        # Verify
        consumers = list(Consumer.get_collection().find({'id' : id}))
        self.assertEqual(0, len(consumers))

    def test_delete_consumer_no_consumer(self):
        """
        Tests that unregistering a consumer that doesn't exist raises the appropriate error.
        """

        # Test
        try:
            self.manager.unregister('fake consumer')
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue('fake consumer' in e)


    def test_update_consumer(self):
        """
        Tests the case of successfully updating a consumer.
        """

        # Setup
        self.manager.register('update-me', display_name='display_name_1', description='description_1', notes={'a' : 'a'})

        delta = {
            'display_name' : 'display_name_2',
            'description'  : 'description_2',
            'disregard'    : 'ignored',
        }

        # Test
        updated = self.manager.update('update-me', delta)

        # Verify
        consumer = Consumer.get_collection().find_one({'id' : 'update-me'})
        self.assertEqual(consumer['display_name'], delta['display_name'])
        self.assertEqual(consumer['description'], delta['description'])

        self.assertEqual(updated['display_name'], delta['display_name'])
        self.assertEqual(updated['description'], delta['description'])

    def test_update_missing_consumer(self):
        """
        Tests updating a consumer that isn't there raises the appropriate exception.
        """

        # Test
        try:
            self.manager.update('not-there', {})
            self.fail('Exception expected')
        except exceptions.MissingResource, e:
            self.assertTrue('not-there' in e)

class UtilityMethodsTests(testutil.PulpTest):

    def test_is_consumer_id_valid(self):
        """
        Tests the consumer ID validation with both valid and invalid IDs.
        """

        # Test
        self.assertTrue(consumer_manager.is_consumer_id_valid('consumer'))
        self.assertTrue(consumer_manager.is_consumer_id_valid('consumer1'))
        self.assertTrue(consumer_manager.is_consumer_id_valid('consumer-1'))
        self.assertTrue(consumer_manager.is_consumer_id_valid('consumer_1'))
        self.assertTrue(consumer_manager.is_consumer_id_valid('_consumer'))

        self.assertTrue(not consumer_manager.is_consumer_id_valid('consumer 1'))
        self.assertTrue(not consumer_manager.is_consumer_id_valid('consumer#1'))
        self.assertTrue(not consumer_manager.is_consumer_id_valid('consumer!'))


class BindManagerTests(testutil.PulpTest):

    CONSUMER_ID = 'mycon'
    REPO_ID = 'myrepo'
    DISTRIBUTOR_ID = 'mydist'
    QUERY = dict(
        consumer_id=CONSUMER_ID,
        repo_id=REPO_ID,
        distributor_id=DISTRIBUTOR_ID,
    )

    def setUp(self):
        testutil.PulpTest.setUp(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        plugin_loader._create_loader()
        mock_plugins.install()

    def tearDown(self):
        testutil.PulpTest.tearDown(self)
        Consumer.get_collection().remove()
        Repo.get_collection().remove()
        RepoDistributor.get_collection().remove()
        Bind.get_collection().remove()
        mock_plugins.reset()

    def clean(self):
        testutil.PulpTest.clean(self)

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
        self.assertTrue(len(binds), 0)
        
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
        self.assertTrue(len(binds), 0)