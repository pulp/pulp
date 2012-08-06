# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import os
import shutil
import traceback
import unittest

from base import PulpAsyncServerTests

from pulp.server import exceptions as pulp_exceptions
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.consumer import Consumer, ConsumerGroup
from pulp.server.managers import factory as managers_factory
from pulp.server.managers.consumer.group import cud


class ConsumerGroupManagerInstantiationTests(unittest.TestCase):

    def test_constructor(self):
        try:
            ConsumerGroup('contructor_group')
        except:
            self.fail(traceback.format_exc())

    def test_factory(self):
        try:
            managers_factory.consumer_group_manager()
        except:
            self.fail(traceback.format_exc())


class ConsumerGroupTests(PulpAsyncServerTests):

    def setUp(self):
        super(ConsumerGroupTests, self).setUp()
        self.collection = ConsumerGroup.get_collection()
        self.manager = cud.ConsumerGroupManager()

    def tearDown(self):
        super(ConsumerGroupTests, self).tearDown()
        self.manager = None
        Consumer.get_collection().remove(safe=True)
        ConsumerGroup.get_collection().remove(safe=True)

    def _create_consumer(self, consumer_id):
        manager = managers_factory.consumer_manager()
        return manager.register(consumer_id)


class ConsumerGroupCUDTests(ConsumerGroupTests):

    def test_create(self):
        group_id = 'create_consumer_group'
        self.manager.create_consumer_group(group_id)
        group = self.collection.find_one({'id': group_id})
        self.assertFalse(group is None)

    def test_create_duplicate_id(self):
        group_id = 'already_exists'
        self.manager.create_consumer_group(group_id)
        self.assertRaises(pulp_exceptions.DuplicateResource,
                          self.manager.create_consumer_group,
                          group_id)

    def test_update_display_name(self):
        group_id = 'update_me'
        original_display_name = 'Update Me'
        self.manager.create_consumer_group(group_id, display_name=original_display_name)

        group = self.collection.find_one({'id': group_id})
        self.assertTrue(group['display_name'] == original_display_name)

        new_display_name = 'Updated!'
        self.manager.update_consumer_group(group_id, display_name=new_display_name)

        group = self.collection.find_one({'id': group_id})
        self.assertFalse(group['display_name'] == original_display_name)
        self.assertTrue(group['display_name'] == new_display_name)

    def test_update_description(self):
        group_id = 'update_me'
        original_description = 'This is a consumer group that needs to be updated :P'
        self.manager.create_consumer_group(group_id, description=original_description)

        group = self.collection.find_one({'id': group_id})
        self.assertTrue(group['description'] == original_description)

        new_description = 'This consumer group has been updated! :D'
        self.manager.update_consumer_group(group_id, description=new_description)

        group = self.collection.find_one({'id': group_id})
        self.assertFalse(group['description'] == original_description)
        self.assertTrue(group['description'] == new_description)

    def test_update_notes(self):
        group_id = 'notes'
        original_notes = {'key_1': 'blonde', 'key_3': 'brown'}
        self.manager.create_consumer_group(group_id, notes=original_notes)

        group = self.collection.find_one({'id': group_id})
        self.assertTrue(group['notes'] == original_notes)

        delta = {'key_2': 'ginger', 'key_3': ''}
        self.manager.update_consumer_group(group_id, notes=delta)

        group = self.collection.find_one({'id': group_id})
        self.assertEqual(group['notes'].get('key_1', None), 'blonde')
        self.assertEqual(group['notes'].get('key_2', None), 'ginger')
        self.assertTrue('key_3' not in group['notes'])

    def test_set_note(self):
        group_id = 'noteworthy'
        self.manager.create_consumer_group(group_id)

        key = 'package'
        value = ['package_dependencies']
        note = {key: value}
        self.manager.set_note(group_id, key, value)

        group = self.collection.find_one({'id': group_id})
        self.assertTrue(group['notes'] == note)

    def test_unset_note(self):
        group_id = 'not_noteworthy'
        notes = {'marital_status': 'polygamist'}
        self.manager.create_consumer_group(group_id, notes=notes)

        group = self.collection.find_one({'id': group_id})
        self.assertTrue(group['notes'] == notes)

        self.manager.unset_note(group_id, 'marital_status')

        group = self.collection.find_one({'id': group_id})
        self.assertFalse(group['notes'])

    def test_delete(self):
        # Setup
        group_id = 'delete_me'
        self.manager.create_consumer_group(group_id)

        group = self.collection.find_one({'id': group_id})
        self.assertFalse(group is None)

        # Test
        self.manager.delete_consumer_group(group_id)

        # Verify
        group = self.collection.find_one({'id': group_id})
        self.assertTrue(group is None)


class ConsumerGroupMembershipTests(ConsumerGroupTests):

    def test_add_single(self):
        group_id = 'test_group'
        self.manager.create_consumer_group(group_id)

        consumer = self._create_consumer('test_consumer')
        criteria = Criteria(filters={'id': consumer['id']}, fields=['id'])
        self.manager.associate(group_id, criteria)

        group = self.collection.find_one({'id': group_id})
        self.assertTrue(consumer['id'] in group['consumer_ids'])

    def test_remove_single(self):
        group_id = 'test_group'
        consumer = self._create_consumer('test_consumer')
        self.manager.create_consumer_group(group_id, consumer_ids=[consumer['id']])

        group = self.collection.find_one({'id': group_id})
        self.assertTrue(consumer['id'] in group['consumer_ids'])

        criteria = Criteria(filters={'id': consumer['id']}, fields=['id'])
        self.manager.unassociate(group_id, criteria)

        group = self.collection.find_one({'id': group_id})
        self.assertFalse(consumer['id'] in group['consumer_ids'])

    def test_unregister(self):
        group_id = 'delete_from_me'
        consumer = self._create_consumer('delete_me')
        self.manager.create_consumer_group(group_id, consumer_ids=[consumer['id']])

        group = self.collection.find_one({'id': group_id})
        self.assertTrue(consumer['id'] in group['consumer_ids'])

        consumer_manager = managers_factory.consumer_manager()
        consumer_manager.unregister(consumer['id'])

        group = self.collection.find_one({'id': group_id})
        self.assertFalse(consumer['id'] in group['consumer_ids'])

    def test_associate_id_regex(self):
        group_id = 'associate_by_regex'
        self.manager.create_consumer_group(group_id)

        consumer_1 = self._create_consumer('consumer_1')
        consumer_2 = self._create_consumer('consumer_2')
        criteria = Criteria(filters={'id': {'$regex': 'consumer_[12]'}})
        self.manager.associate(group_id, criteria)

        group = self.collection.find_one({'id': group_id})
        self.assertTrue(consumer_1['id'] in group['consumer_ids'])
        self.assertTrue(consumer_2['id'] in group['consumer_ids'])


