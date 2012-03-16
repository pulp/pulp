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
from pulp.server.db.model.gc_consumer import Consumer
import pulp.server.managers.consumer.cud as consumer_manager
import pulp.server.managers.consumer.notes as consumer_notes_manager
import pulp.server.managers.factory as manager_factory
import pulp.server.exceptions as exceptions

# -- test cases ---------------------------------------------------------------

class ConsumerNotesManagerTests(testutil.PulpTest):

    def setUp(self):
        testutil.PulpTest.setUp(self)

        plugin_loader._create_loader()
        mock_plugins.install()

        # Create the manager instances to test
        self.consumer_manager = consumer_manager.ConsumerManager()
        self.consumer_notes_manager = consumer_notes_manager.ConsumerNotesManager()

    def tearDown(self):
        testutil.PulpTest.tearDown(self)
        mock_plugins.reset()

    def clean(self):
        testutil.PulpTest.clean(self)
        Consumer.get_collection().remove()
        
    def test_add_notes(self):
        """
        Tests adding notes to a consumer.
        """

        # Setup
        id = 'consumer_1'
        name = 'Consumer 1'
        description = 'Test Consumer 1'
        created = self.consumer_manager.register(id, name, description)
        
        consumers = list(Consumer.get_collection().find())
        self.assertEqual(1, len(consumers))
        
        # Test
        consumer = consumers[0]
        self.assertEqual(consumer['notes'], {})
        
        notes = {'note1' : 'value1'}
        self.consumer_notes_manager.add_notes(id, notes)
        
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
        created = self.consumer_manager.register(id, name, description, notes)
        
        consumers = list(Consumer.get_collection().find())
        self.assertEqual(1, len(consumers))
        consumer = consumers[0]
        self.assertEqual(consumer['notes'], notes)
        
        # Test
        updated_notes = {'note1' : 'new-value1', 'note2' : 'new-value2'}
        self.consumer_notes_manager.update_notes(id, updated_notes)
        
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
        created = self.consumer_manager.register(id, name, description, notes)
        
        # Test
        removed_notes = {'note1' : 'value1'}
        self.consumer_notes_manager.remove_notes(id, removed_notes)

        # Verify
        consumers = list(Consumer.get_collection().find())
        consumer = consumers[0]
        self.assertEqual(consumer['notes'], {'note2' : 'value2'})
        
    def test_add_update_remove_notes_with_nonexisting_consumer(self):
        # Setup
        id = 'non_existing_consumer'
        
        # Try adding notes
        notes = {'note1' : 'value1'}
        try:
            self.consumer_notes_manager.add_notes(id, notes)
            self.fail('Missing Consumer did not raise an exception')
        except exceptions.MissingResource, e:
            self.assertTrue(id in e)
            print(e)
            
        # Try updating notes
        notes = {'note1' : 'new-value1'}
        try:
            self.consumer_notes_manager.update_notes(id, notes)
            self.fail('Missing Consumer did not raise an exception')
        except exceptions.MissingResource, e:
            self.assertTrue(id in e)
            print(e)
            
        # Try removing notes
        notes = {'note1' : 'new-value1'}
        try:
            self.consumer_notes_manager.remove_notes(id, notes)
            self.fail('Missing Consumer did not raise an exception')
        except exceptions.MissingResource, e:
            self.assertTrue(id in e)
            print(e)

            
    def test_add_update_remove_notes_with_invalid_notes(self):
        # Setup
        id = 'consumer_1'
        name = 'Consumer 1'
        description = 'Test Consumer 1'
        created = self.consumer_manager.register(id, name, description)
        
        notes = "invalid_string_format_notes"
        
        # Test add_notes
        try:
            self.consumer_notes_manager.add_notes(id, notes)
            self.fail('Invalid notes did not raise an exception')
        except exceptions.InvalidValue, e:
            self.assertTrue(notes in e)
            print(e)
        
        # Test update_notes
        try:
            self.consumer_notes_manager.update_notes(id, notes)
            self.fail('Invalid notes did not raise an exception')
        except exceptions.InvalidValue, e:
            self.assertTrue(notes in e)
            print(e)
            
        # Test remove_notes
        try:
            self.consumer_notes_manager.remove_notes(id, notes)
            self.fail('Invalid notes did not raise an exception')
        except exceptions.InvalidValue, e:
            self.assertTrue(notes in e)
            print(e)
