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

import base
import mock_plugins
import mock_agent

import pulp.plugins.loader as plugin_loader
from pulp.server.db.model.consumer import Consumer, Bind, ConsumerHistoryEvent
from pulp.server.db.model.repository import Repo, RepoDistributor
from pulp.server.exceptions import MissingResource
import pulp.server.managers.consumer.cud as consumer_manager
import pulp.server.managers.consumer.history as history_manager
import pulp.server.managers.factory as factory
import pulp.server.exceptions as exceptions


# -- test cases ---------------------------------------------------------------

class ConsumerManagerTests(base.PulpServerTests):

    def setUp(self):
        base.PulpServerTests.setUp(self)
        plugin_loader._create_loader()
        mock_plugins.install()
        mock_agent.install()

        # Create the manager instance to test
        self.manager = consumer_manager.ConsumerManager()

    def tearDown(self):
        base.PulpServerTests.tearDown(self)
        mock_plugins.reset()

    def clean(self):
        base.PulpServerTests.clean(self)

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
        print created

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
            self.assertTrue(['id'] in e)
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
            print e
            self.assertTrue(['notes'] in e)
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
            self.assertTrue('fake consumer' == e.resources['consumer'])


    def test_update_consumer(self):
        """
        Tests the case of successfully updating a consumer.
        """

        # Setup
        self.manager.register('update-me', display_name='display_name_1', description='description_1', notes={'a' : 'a'})

        delta = {
            'display-name' : 'display_name_2',
            'description'  : 'description_2',
            'disregard'    : 'ignored',
        }

        # Test
        updated = self.manager.update('update-me', delta)

        # Verify
        consumer = Consumer.get_collection().find_one({'id' : 'update-me'})
        self.assertEqual(consumer['display_name'], delta['display-name'])
        self.assertEqual(consumer['description'], delta['description'])

        self.assertEqual(updated['display_name'], delta['display-name'])
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
            self.assertTrue('not-there' == e.resources['consumer'])

    def test_add_notes(self):
        """
        Tests adding notes to a consumer.
        """

        # Setup
        id = 'consumer_1'
        name = 'Consumer 1'
        description = 'Test Consumer 1'
        created = self.manager.register(id, name, description)

        consumers = list(Consumer.get_collection().find())
        self.assertEqual(1, len(consumers))

        # Test
        consumer = consumers[0]
        self.assertEqual(consumer['notes'], {})

        notes = {'note1' : 'value1', 'note2' : 'value2'}
        self.manager.update(id, delta={'notes':notes})

        # Verify
        consumers = list(Consumer.get_collection().find())
        consumer = consumers[0]
        self.assertEqual(consumer['notes'], notes)


    def test_update_notes(self):
        """
        Tests updating notes of a consumer
        """

        # Setup
        id = 'consumer_1'
        name = 'Consumer 1'
        description = 'Test Consumer 1'
        notes = {'note1' : 'value1', 'note2' : 'value2'}
        created = self.manager.register(id, name, description, notes)

        consumers = list(Consumer.get_collection().find())
        self.assertEqual(1, len(consumers))
        consumer = consumers[0]
        self.assertEqual(consumer['notes'], notes)

        # Test
        updated_notes = {'note1' : 'new-value1', 'note2' : 'new-value2'}
        self.manager.update(id, delta={'notes':updated_notes})

        # Verify
        consumers = list(Consumer.get_collection().find())
        consumer = consumers[0]
        self.assertEqual(consumer['notes'], updated_notes)

    def test_delete_notes(self):
        """
        Tests removing notes from a consumer
        """

        # Setup
        id = 'consumer_1'
        name = 'Consumer 1'
        description = 'Test Consumer 1'
        notes = {'note1' : 'value1', 'note2' : 'value2'}
        created = self.manager.register(id, name, description, notes)

        # Test
        removed_notes = {'note1' : None}
        self.manager.update(id, delta={'notes':removed_notes})

        # Verify
        consumers = list(Consumer.get_collection().find())
        consumer = consumers[0]
        self.assertEqual(consumer['notes'], {'note2' : 'value2'})

    def test_add_update_remove_notes_with_nonexisting_consumer(self):
        # Setup
        id = 'non_existing_consumer'

        # Try adding and deleting notes from a non-existing consumer
        notes = {'note1' : 'value1', 'note2' : None}
        try:
            self.manager.update(id, delta={'notes':notes})
            self.fail('Missing Consumer did not raise an exception')
        except exceptions.MissingResource, e:
            print e
            self.assertTrue(id == e.resources['consumer'])


    def test_add_update_remove_notes_with_invalid_notes(self):
        # Setup
        id = 'consumer_1'
        name = 'Consumer 1'
        description = 'Test Consumer 1'
        created = self.manager.register(id, name, description)

        notes = "invalid_string_format_notes"

        # Test add_notes
        try:
            self.manager.update(id, delta={'notes':notes})
            self.fail('Invalid notes did not raise an exception')
        except exceptions.InvalidValue, e:
            self.assertTrue("delta['notes']" in e)
            print(e)


        
        
class ConsumerHistoryManagerTests(base.PulpServerTests):

    def setUp(self):
        base.PulpServerTests.setUp(self)
        plugin_loader._create_loader()
        mock_plugins.install()
        mock_agent.install()

        # Create manager instances to test
        self.consumer_manager = consumer_manager.ConsumerManager()
        self.history_manager = history_manager.ConsumerHistoryManager()
        
    def tearDown(self):
        base.PulpServerTests.tearDown(self)
        mock_plugins.reset()

    def clean(self):
        base.PulpServerTests.clean(self)
                
        Consumer.get_collection().remove()
        ConsumerHistoryEvent.get_collection().remove()
        
    def test_record_register_unregister(self):
        """
        Tests adding a history record for consumer register and unregister.
        """
        # Setup
        cid = "abc"
        self.consumer_manager.register(cid)
        self.consumer_manager.unregister(cid)
        
        # Test
        entries = self.history_manager.query()
        self.assertEqual(2, len(entries))

        # Verify
        entry = entries[0]
        self.assertEqual(entry['consumer_id'], cid)
        self.assertEqual(entry['type'], history_manager.TYPE_CONSUMER_REGISTERED)
        self.assertTrue(entry['timestamp'] is not None)

        entry = entries[1]
        self.assertEqual(entry['consumer_id'], cid)
        self.assertEqual(entry['type'], history_manager.TYPE_CONSUMER_UNREGISTERED)
        self.assertTrue(entry['timestamp'] is not None)        


class UtilityMethodsTests(base.PulpServerTests):

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
