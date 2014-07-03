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

from mock import patch

from pulp.server.db.model.consumer import Consumer, ConsumerHistoryEvent
import pulp.server.managers.consumer.cud as consumer_manager
import pulp.server.managers.consumer.history as history_manager
import pulp.server.exceptions as exceptions


# -- test cases ---------------------------------------------------------------

class ConsumerManagerTests(base.PulpServerTests):

    def setUp(self):
        super(ConsumerManagerTests, self).setUp()

        # Create the manager instance to test
        self.manager = consumer_manager.ConsumerManager()

    def tearDown(self):
        super(ConsumerManagerTests, self).tearDown()

    def clean(self):
        base.PulpServerTests.clean(self)

        Consumer.get_collection().remove()

    def test_registration(self):
        """
        Tests creating a consumer with valid data is successful.
        """

        # Setup
        consumer_id = 'consumer_1'
        name = 'Consumer 1'
        description = 'Test Consumer 1'
        notes = {'note1': 'value1'}
        capabilities = {}
        rsa_pub = 'fake-key'

        # Test
        created, certificate = self.manager.register(
            consumer_id, name, description, notes=notes, capabilities=capabilities, rsa_pub=rsa_pub)

        # Verify
        consumers = list(Consumer.get_collection().find())
        self.assertEqual(1, len(consumers))

        consumer = consumers[0]
        self.assertEqual(consumer_id, consumer['id'])
        self.assertEqual(name, consumer['display_name'])
        self.assertEqual(description, consumer['description'])
        self.assertEqual(notes, consumer['notes'])
        self.assertEqual(rsa_pub, consumer['rsa_pub'])

        self.assertEqual(consumer_id, created['id'])
        self.assertEqual(name, created['display_name'])
        self.assertEqual(description, created['description'])
        self.assertEqual(notes, created['notes'])
        self.assertEqual(rsa_pub, consumer['rsa_pub'])

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
        consumer_id = 'duplicate'
        self.manager.register(consumer_id)

        # Test
        try:
            self.manager.register(consumer_id)
            self.fail('Consumer with an existing ID did not raise an exception')
        except exceptions.DuplicateResource, e:
            self.assertTrue(consumer_id in e)
            print(e) # for coverage

    def test_create_invalid_notes(self):
        """
        Tests that creating a consumer but passing a non-dict as the notes field
        raises the correct exception.
        """

        # Setup
        consumer_id = 'bad-notes'
        notes = 'not a dict'

        # Test
        try:
            self.manager.register(consumer_id, notes=notes)
            self.fail('Invalid notes did not cause create to raise an exception')
        except exceptions.InvalidValue, e:
            print e
            self.assertTrue(['notes'] in e)
            print(e) # for coverage

    @patch('pulp.server.managers.consumer.agent.AgentManager.unregistered')
    def test_unregister_consumer(self, mock_unreg):
        """
        Tests unregistering a consumer under normal circumstances.
        """

        # Setup
        consumer_id = 'doomed'
        self.manager.register(consumer_id)

        # Test
        self.manager.unregister(consumer_id)

        # Verify
        consumers = list(Consumer.get_collection().find({'id' : consumer_id}))
        self.assertEqual(0, len(consumers))
        mock_unreg.assert_called_with(consumer_id)

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
        self.manager.register(
            'update-me', display_name='display_name_1', description='description_1', notes={'a': 'a'})

        delta = {
            'display_name': 'display_name_2',
            'description': 'description_2',
            'rsa_pub': 'rsa_pub_2',
            'disregard': 'ignored',
        }

        # Test
        updated = self.manager.update('update-me', delta)

        # Verify
        consumer = Consumer.get_collection().find_one({'id': 'update-me'})
        self.assertEqual(consumer['display_name'], delta['display_name'])
        self.assertEqual(consumer['description'], delta['description'])
        self.assertEqual(consumer['rsa_pub'], delta['rsa_pub'])
        self.assertEqual(updated['display_name'], delta['display_name'])
        self.assertEqual(updated['description'], delta['description'])
        self.assertEqual(updated['rsa_pub'], delta['rsa_pub'])

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
        consumer_id = 'consumer_1'
        name = 'Consumer 1'
        description = 'Test Consumer 1'
        self.manager.register(consumer_id, name, description)

        consumers = list(Consumer.get_collection().find())
        self.assertEqual(1, len(consumers))

        # Test
        consumer = consumers[0]
        self.assertEqual(consumer['notes'], {})

        notes = {'note1' : 'value1', 'note2' : 'value2'}
        self.manager.update(consumer_id, delta={'notes':notes})

        # Verify
        consumers = list(Consumer.get_collection().find())
        consumer = consumers[0]
        self.assertEqual(consumer['notes'], notes)

    def test_update_notes(self):
        """
        Tests updating notes of a consumer
        """

        # Setup
        consumer_id = 'consumer_1'
        name = 'Consumer 1'
        description = 'Test Consumer 1'
        notes = {'note1' : 'value1', 'note2' : 'value2'}
        self.manager.register(consumer_id, name, description, notes)

        consumers = list(Consumer.get_collection().find())
        self.assertEqual(1, len(consumers))
        consumer = consumers[0]
        self.assertEqual(consumer['notes'], notes)

        # Test
        updated_notes = {'note1' : 'new-value1', 'note2' : 'new-value2'}
        self.manager.update(consumer_id, delta={'notes':updated_notes})

        # Verify
        consumers = list(Consumer.get_collection().find())
        consumer = consumers[0]
        self.assertEqual(consumer['notes'], updated_notes)

    def test_delete_notes(self):
        """
        Tests removing notes from a consumer
        """

        # Setup
        consumer_id = 'consumer_1'
        name = 'Consumer 1'
        description = 'Test Consumer 1'
        notes = {'note1' : 'value1', 'note2' : 'value2'}
        self.manager.register(consumer_id, name, description, notes)

        # Test
        removed_notes = {'note1' : None}
        self.manager.update(consumer_id, delta={'notes':removed_notes})

        # Verify
        consumers = list(Consumer.get_collection().find())
        consumer = consumers[0]
        self.assertEqual(consumer['notes'], {'note2' : 'value2'})

    def test_add_update_remove_notes_with_nonexisting_consumer(self):
        # Setup
        consumer_id = 'non_existing_consumer'

        # Try adding and deleting notes from a non-existing consumer
        notes = {'note1' : 'value1', 'note2' : None}
        try:
            self.manager.update(consumer_id, delta={'notes':notes})
            self.fail('Missing Consumer did not raise an exception')
        except exceptions.MissingResource, e:
            print e
            self.assertTrue(consumer_id == e.resources['consumer'])

    def test_add_update_remove_notes_with_invalid_notes(self):
        # Setup
        consumer_id = 'consumer_1'
        name = 'Consumer 1'
        description = 'Test Consumer 1'
        self.manager.register(consumer_id, name, description)

        notes = "invalid_string_format_notes"

        # Test add_notes
        try:
            self.manager.update(consumer_id, delta={'notes':notes})
            self.fail('Invalid notes did not raise an exception')
        except exceptions.InvalidValue, e:
            self.assertTrue("delta['notes']" in e)
            print(e)


class ConsumerHistoryManagerTests(base.PulpServerTests):

    def setUp(self):
        super(ConsumerHistoryManagerTests, self).setUp()

        # Create manager instances to test
        self.consumer_manager = consumer_manager.ConsumerManager()
        self.history_manager = history_manager.ConsumerHistoryManager()

    def tearDown(self):
        super(ConsumerHistoryManagerTests, self).tearDown()

    def clean(self):
        base.PulpServerTests.clean(self)

        Consumer.get_collection().remove()
        ConsumerHistoryEvent.get_collection().remove()

    def test_record_register(self):
        """
        Tests adding a history record for consumer register and unregister.
        """
        # Setup
        cid = "abc"
        self.consumer_manager.register(cid)

        # Test register
        entries = self.history_manager.query()
        self.assertEqual(1, len(entries))

        # Verify
        entry = entries[0]
        self.assertEqual(entry['consumer_id'], cid)
        self.assertEqual(entry['type'], history_manager.TYPE_CONSUMER_REGISTERED)
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
        self.assertTrue(consumer_manager.is_consumer_id_valid('consumer.1.2'))

        self.assertTrue(not consumer_manager.is_consumer_id_valid('consumer 1'))
        self.assertTrue(not consumer_manager.is_consumer_id_valid('consumer#1'))
        self.assertTrue(not consumer_manager.is_consumer_id_valid('consumer!'))
