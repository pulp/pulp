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

import traceback
import unittest

from .....import base
from mock import patch

from pulp.devel.unit.base import PulpCeleryTaskTests
from pulp.devel.unit.server import util
from pulp.server.async.tasks import TaskResult
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.consumer import Consumer, ConsumerGroup
from pulp.server.exceptions import MissingResource, PulpException, error_codes
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


class ConsumerGroupTests(base.PulpServerTests):

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
        consumer, certificate = manager.register(consumer_id)
        return consumer


class ConsumerGroupCUDTests(ConsumerGroupTests):

    def test_create(self):
        group_id = 'create_consumer_group'
        self.manager.create_consumer_group(group_id)
        group = self.collection.find_one({'id': group_id})
        self.assertFalse(group is None)

    def test_create_with_consumer(self):
        group_id = 'create_consumer_group'
        self._create_consumer('test_consumer')
        self.manager.create_consumer_group(group_id, consumer_ids=['test_consumer'])
        group = self.collection.find_one({'id': group_id})
        self.assertFalse(group is None)

    def test_create_invalid_consumer_id(self):
        group_id = 'create_consumer_group'
        # Add one valid consumer
        self._create_consumer('test_consumer')

        util.assert_validation_exception(self.manager.create_consumer_group, [error_codes.PLP1001],
                                         group_id, consumer_ids=['test_consumer', 'bad1'])
        group = self.collection.find_one({'id': group_id})
        self.assertFalse(group is not None)

    def test_create_duplicate_id(self):
        group_id = 'already_exists'
        self.manager.create_consumer_group(group_id)
        util.assert_validation_exception(self.manager.create_consumer_group, [error_codes.PLP1004],
                                         group_id)

    def test_create_invalid_id(self):
        group_id = '**invalid/id**'
        util.assert_validation_exception(self.manager.create_consumer_group, [error_codes.PLP1003],
                                         group_id)

    def test_create_missing_id(self):
        group_id = None
        util.assert_validation_exception(self.manager.create_consumer_group, [error_codes.PLP1002],
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
        group = self.collection.find_one({'id': group_id})

        consumer = self._create_consumer('test_consumer')
        self.assertFalse(consumer['id'] in group['consumer_ids'])
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

    @patch('pulp.server.managers.factory.consumer_agent_manager')
    def test_unregister(self, unused):
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


class TestBind(PulpCeleryTaskTests):

    @patch('pulp.server.managers.consumer.group.cud.bind_task')
    @patch('pulp.server.managers.factory.consumer_group_query_manager')
    def test_bind_no_errors(self, mock_query_manager, mock_bind):
        mock_query_manager.return_value.get_group.return_value = {'consumer_ids': ['foo-consumer']}
        binding_config = {'binding': 'foo'}
        agent_options = {'bar': 'baz'}
        mock_bind.return_value = TaskResult(spawned_tasks=[{'task_id': 'foo-request-id'}])
        result = cud.bind('foo_group_id', 'foo_repo_id', 'foo_distributor_id',
                          True, binding_config, agent_options)
        mock_bind.assert_called_once_with('foo-consumer', 'foo_repo_id', 'foo_distributor_id',
                                          True, binding_config, agent_options)
        self.assertEquals(result.spawned_tasks[0], {'task_id': 'foo-request-id'})

    @patch('pulp.server.managers.consumer.group.cud.bind_task')
    @patch('pulp.server.managers.factory.consumer_group_query_manager')
    def test_bind_with_missing_resource_errors(self, mock_query_manager, mock_bind):
        mock_query_manager.return_value.get_group.return_value = {'consumer_ids': ['foo-consumer']}
        binding_config = {'binding': 'foo'}
        agent_options = {'bar': 'baz'}
        side_effect_exception = MissingResource()
        mock_bind.side_effect = side_effect_exception

        result = cud.bind('foo_group_id', 'foo_repo_id', 'foo_distributor_id',
                          True, binding_config, agent_options)
        self.assertTrue(result.error.error_code is error_codes.PLP0004)
        self.assertEquals(result.error.child_exceptions[0], side_effect_exception)

    @patch('pulp.server.managers.consumer.group.cud.bind_task')
    @patch('pulp.server.managers.factory.consumer_group_query_manager')
    def test_bind_with_general_error(self, mock_query_manager, mock_bind):
        mock_query_manager.return_value.get_group.return_value = {'consumer_ids': ['foo-consumer']}
        binding_config = {'binding': 'foo'}
        agent_options = {'bar': 'baz'}
        side_effect_exception = ValueError()
        mock_bind.side_effect = side_effect_exception

        result = cud.bind('foo_group_id', 'foo_repo_id', 'foo_distributor_id',
                          True, binding_config, agent_options)
        self.assertTrue(isinstance(result.error, PulpException))
        self.assertEquals(result.error.error_code, error_codes.PLP0004)
        self.assertEquals(result.error.child_exceptions[0], side_effect_exception)


class TestUnbind(PulpCeleryTaskTests):

    @patch('pulp.server.managers.consumer.group.cud.unbind_task')
    @patch('pulp.server.managers.factory.consumer_group_query_manager')
    def test_bind_no_errors(self, mock_query_manager, mock_unbind):
        mock_query_manager.return_value.get_group.return_value = {'consumer_ids': ['foo-consumer']}
        options = {'bar': 'baz'}
        mock_unbind.return_value = TaskResult(spawned_tasks=[{'task_id': 'foo-request-id'}])
        result = cud.unbind('foo_group_id', 'foo_repo_id', 'foo_distributor_id', options)
        mock_unbind.assert_called_once_with('foo-consumer', 'foo_repo_id', 'foo_distributor_id',
                                            options)
        self.assertEquals(result.spawned_tasks[0], {'task_id': 'foo-request-id'})

    @patch('pulp.server.managers.consumer.group.cud.unbind_task')
    @patch('pulp.server.managers.factory.consumer_group_query_manager')
    def test_bind_with_missing_resource_errors(self, mock_query_manager, mock_unbind):
        mock_query_manager.return_value.get_group.return_value = {'consumer_ids': ['foo-consumer']}
        options = {'bar': 'baz'}
        side_effect_exception = MissingResource()
        mock_unbind.side_effect = side_effect_exception

        result = cud.unbind('foo_group_id', 'foo_repo_id', 'foo_distributor_id', options)
        self.assertTrue(isinstance(result.error, PulpException))
        self.assertEquals(result.error.error_code, error_codes.PLP0005)
        self.assertEquals(result.error.child_exceptions[0], side_effect_exception)

    @patch('pulp.server.managers.consumer.group.cud.unbind_task')
    @patch('pulp.server.managers.factory.consumer_group_query_manager')
    def test_bind_with_general_error(self, mock_query_manager, mock_unbind):
        mock_query_manager.return_value.get_group.return_value = {'consumer_ids': ['foo-consumer']}
        options = {'bar': 'baz'}
        side_effect_exception = ValueError()
        mock_unbind.side_effect = side_effect_exception

        result = cud.unbind('foo_group_id', 'foo_repo_id', 'foo_distributor_id', options)
        self.assertTrue(isinstance(result.error, PulpException))
        self.assertEquals(result.error.error_code, error_codes.PLP0005)
        self.assertEquals(result.error.child_exceptions[0], side_effect_exception)


class TestInstallContent(unittest.TestCase):

    @patch('pulp.server.managers.factory.consumer_agent_manager')
    @patch('pulp.server.managers.factory.consumer_group_query_manager')
    def test_install(self, mock_query_manager, mock_agent_manager):
        mock_query_manager.return_value.get_group.return_value = {'consumer_ids': ['foo-consumer']}
        group_id = 'foo-group'
        units = ['foo', 'bar']
        agent_options = {'bar': 'baz'}
        mock_task = mock_agent_manager.return_value.install_content

        mock_task.return_value = {'task_id': 'foo-request-id'}
        result = cud.ConsumerGroupManager.install_content(group_id, units, agent_options)

        mock_task.assert_called_once_with('foo-consumer', units, agent_options)
        self.assertEquals(result.spawned_tasks[0], {'task_id': 'foo-request-id'})

    @patch('pulp.server.managers.factory.consumer_agent_manager')
    @patch('pulp.server.managers.factory.consumer_group_query_manager')
    def test_install_with_missing_resource_errors(self, mock_query_manager, mock_agent_manager):
        mock_query_manager.return_value.get_group.return_value = {'consumer_ids': ['foo-consumer']}
        group_id = 'foo-group'
        units = ['foo', 'bar']
        agent_options = {'bar': 'baz'}
        mock_task = mock_agent_manager.return_value.install_content
        side_effect_exception = MissingResource()
        mock_task.side_effect = side_effect_exception

        result = cud.ConsumerGroupManager.install_content(group_id, units, agent_options)

        self.assertTrue(isinstance(result.error, PulpException))
        self.assertEquals(result.error.error_code, error_codes.PLP0020)
        self.assertEquals(result.error.child_exceptions[0], side_effect_exception)

    @patch('pulp.server.managers.factory.consumer_agent_manager')
    @patch('pulp.server.managers.factory.consumer_group_query_manager')
    def test_install_with_general_error(self, mock_query_manager, mock_agent_manager):
        mock_query_manager.return_value.get_group.return_value = {'consumer_ids': ['foo-consumer']}
        group_id = 'foo-group'
        units = ['foo', 'bar']
        agent_options = {'bar': 'baz'}
        mock_task = mock_agent_manager.return_value.install_content
        side_effect_exception = ValueError()
        mock_task.side_effect = side_effect_exception

        result = cud.ConsumerGroupManager.install_content(group_id, units, agent_options)

        self.assertTrue(isinstance(result.error, PulpException))
        self.assertEquals(result.error.error_code, error_codes.PLP0020)
        self.assertEquals(result.error.child_exceptions[0], side_effect_exception)


class TestUnInstallContent(unittest.TestCase):

    @patch('pulp.server.managers.factory.consumer_agent_manager')
    @patch('pulp.server.managers.factory.consumer_group_query_manager')
    def test_uninstall(self, mock_query_manager, mock_agent_manager):
        mock_query_manager.return_value.get_group.return_value = {'consumer_ids': ['foo-consumer']}
        group_id = 'foo-group'
        units = ['foo', 'bar']
        agent_options = {'bar': 'baz'}
        mock_task = mock_agent_manager.return_value.uninstall_content

        mock_task.return_value = {'task_id': 'foo-request-id'}
        result = cud.ConsumerGroupManager.uninstall_content(group_id, units, agent_options)

        mock_task.assert_called_once_with('foo-consumer', units, agent_options)
        self.assertEquals(result.spawned_tasks[0], {'task_id': 'foo-request-id'})

    @patch('pulp.server.managers.factory.consumer_agent_manager')
    @patch('pulp.server.managers.factory.consumer_group_query_manager')
    def test_uninstall_with_missing_resource_errors(self, mock_query_manager, mock_agent_manager):
        mock_query_manager.return_value.get_group.return_value = {'consumer_ids': ['foo-consumer']}
        group_id = 'foo-group'
        units = ['foo', 'bar']
        agent_options = {'bar': 'baz'}
        mock_task = mock_agent_manager.return_value.uninstall_content
        side_effect_exception = MissingResource()
        mock_task.side_effect = side_effect_exception

        result = cud.ConsumerGroupManager.uninstall_content(group_id, units, agent_options)

        self.assertTrue(isinstance(result.error, PulpException))
        self.assertEquals(result.error.error_code, error_codes.PLP0022)
        self.assertEquals(result.error.child_exceptions[0], side_effect_exception)

    @patch('pulp.server.managers.factory.consumer_agent_manager')
    @patch('pulp.server.managers.factory.consumer_group_query_manager')
    def test_uninstall_with_general_error(self, mock_query_manager, mock_agent_manager):
        mock_query_manager.return_value.get_group.return_value = {'consumer_ids': ['foo-consumer']}
        group_id = 'foo-group'
        units = ['foo', 'bar']
        agent_options = {'bar': 'baz'}
        mock_task = mock_agent_manager.return_value.uninstall_content
        side_effect_exception = ValueError()
        mock_task.side_effect = side_effect_exception

        result = cud.ConsumerGroupManager.uninstall_content(group_id, units, agent_options)

        self.assertTrue(isinstance(result.error, PulpException))
        self.assertEquals(result.error.error_code, error_codes.PLP0022)
        self.assertEquals(result.error.child_exceptions[0], side_effect_exception)


class TestUpdateContent(unittest.TestCase):

    @patch('pulp.server.managers.factory.consumer_agent_manager')
    @patch('pulp.server.managers.factory.consumer_group_query_manager')
    def test_update(self, mock_query_manager, mock_agent_manager):
        mock_query_manager.return_value.get_group.return_value = {'consumer_ids': ['foo-consumer']}
        group_id = 'foo-group'
        units = ['foo', 'bar']
        agent_options = {'bar': 'baz'}
        mock_task = mock_agent_manager.return_value.update_content

        mock_task.return_value = {'task_id': 'foo-request-id'}
        result = cud.ConsumerGroupManager.update_content(group_id, units, agent_options)

        mock_task.assert_called_once_with('foo-consumer', units, agent_options)
        self.assertEquals(result.spawned_tasks[0], {'task_id': 'foo-request-id'})

    @patch('pulp.server.managers.factory.consumer_agent_manager')
    @patch('pulp.server.managers.factory.consumer_group_query_manager')
    def test_update_with_missing_resource_errors(self, mock_query_manager, mock_agent_manager):
        mock_query_manager.return_value.get_group.return_value = {'consumer_ids': ['foo-consumer']}
        group_id = 'foo-group'
        units = ['foo', 'bar']
        agent_options = {'bar': 'baz'}
        mock_task = mock_agent_manager.return_value.update_content
        side_effect_exception = MissingResource()
        mock_task.side_effect = side_effect_exception

        result = cud.ConsumerGroupManager.update_content(group_id, units, agent_options)

        self.assertTrue(isinstance(result.error, PulpException))
        self.assertEquals(result.error.error_code, error_codes.PLP0021)
        self.assertEquals(result.error.child_exceptions[0], side_effect_exception)

    @patch('pulp.server.managers.factory.consumer_agent_manager')
    @patch('pulp.server.managers.factory.consumer_group_query_manager')
    def test_update_with_general_error(self, mock_query_manager, mock_agent_manager):
        mock_query_manager.return_value.get_group.return_value = {'consumer_ids': ['foo-consumer']}
        group_id = 'foo-group'
        units = ['foo', 'bar']
        agent_options = {'bar': 'baz'}
        mock_task = mock_agent_manager.return_value.update_content
        side_effect_exception = ValueError()
        mock_task.side_effect = side_effect_exception

        result = cud.ConsumerGroupManager.update_content(group_id, units, agent_options)

        self.assertTrue(isinstance(result.error, PulpException))
        self.assertEquals(result.error.error_code, error_codes.PLP0021)
        self.assertEquals(result.error.child_exceptions[0], side_effect_exception)
