# -*- coding: utf-8 -*-
#
# Copyright © 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import unittest

from mock import patch

from pulp.server.async.tasks import TaskResult
from pulp.server.tasks import consumer


class TestBind(unittest.TestCase):

    @patch('pulp.server.tasks.consumer.managers')
    def test_bind_no_agent_notification(self, mock_bind_manager):
        binding_config = {'binding': 'foo'}
        agent_options = {'bar': 'baz'}
        result = consumer.bind('foo_consumer_id', 'foo_repo_id', 'foo_distributor_id',
                               False, binding_config, agent_options)

        mock_bind_manager.consumer_bind_manager.return_value.bind.assert_called_once_with(
            'foo_consumer_id', 'foo_repo_id', 'foo_distributor_id',
            False, binding_config)

        self.assertTrue(isinstance(result, TaskResult))
        self.assertEquals(mock_bind_manager.consumer_bind_manager.return_value.bind.return_value,
                          result.return_value)

        # Make sure we didn't process the agent
        self.assertEquals(result.spawned_tasks, [])
        self.assertFalse(mock_bind_manager.consumer_agent_manager.called)

    @patch('pulp.server.tasks.consumer.managers')
    def test_bind_with_agent_notification(self, mock_bind_manager):
        binding_config = {'binding': 'foo'}
        agent_options = {'bar': 'baz'}
        mock_bind_manager.consumer_agent_manager.return_value.bind.return_value = \
            {'task_id': 'foo-request-id', 'other_task_detail': 'abc123'}
        result = consumer.bind('foo_consumer_id', 'foo_repo_id', 'foo_distributor_id',
                               True, binding_config, agent_options)
        mock_bind_manager.consumer_agent_manager.return_value.bind.assert_called_once_with(
            'foo_consumer_id', 'foo_repo_id', 'foo_distributor_id', agent_options
        )

        self.assertTrue(isinstance(result, TaskResult))
        self.assertEquals(result.return_value,
                          mock_bind_manager.consumer_bind_manager.return_value.bind.return_value)
        self.assertEquals(result.spawned_tasks, [{'task_id': 'foo-request-id'}])


class TestUnbind(unittest.TestCase):

    @patch('pulp.server.tasks.consumer.managers')
    def test_unbind_no_agent_notification(self, mock_bind_manager):
        binding_config = {'notify_agent': False}
        agent_options = {'bar': 'baz'}
        mock_bind_manager.consumer_bind_manager.return_value.get_bind.return_value = binding_config
        result = consumer.unbind('foo_consumer_id', 'foo_repo_id', 'foo_distributor_id',
                                 agent_options)

        mock_bind_manager.consumer_bind_manager.return_value.delete.assert_called_once_with(
            'foo_consumer_id', 'foo_repo_id', 'foo_distributor_id', True)

        self.assertEqual(result.error, None)
        self.assertEqual(result.return_value, {'notify_agent': False})
        self.assertEqual(result.spawned_tasks, [])

        #Make sure we didn't process the agent
        self.assertFalse(mock_bind_manager.consumer_agent_manager.called)

    @patch('pulp.server.tasks.consumer.managers')
    def test_unbind_with_agent_notification(self, mock_bind_manager):
        binding_config = {'notify_agent': True}
        agent_options = {'bar': 'baz'}
        mock_bind_manager.consumer_bind_manager.return_value.get_bind.return_value = binding_config
        mock_bind_manager.consumer_agent_manager.return_value.unbind.return_value = \
            {'task_id': 'foo-request-id', 'other_task_detail': 'abc123'}
        result = consumer.unbind('foo_consumer_id', 'foo_repo_id', 'foo_distributor_id',
                                 agent_options)
        mock_bind_manager.consumer_bind_manager.return_value.unbind.assert_called_once_with(
            'foo_consumer_id', 'foo_repo_id', 'foo_distributor_id')
        mock_bind_manager.consumer_agent_manager.return_value.unbind.assert_called_once_with(
            'foo_consumer_id', 'foo_repo_id', 'foo_distributor_id', agent_options)
        self.assertTrue(isinstance(result, TaskResult))
        self.assertEquals(result.spawned_tasks, [{'task_id': 'foo-request-id'}])


class TestForceUnbind(unittest.TestCase):
    @patch('pulp.server.tasks.consumer.managers')
    def test_unbind_no_agent_notification(self, mock_bind_manager):
        binding_config = {'notify_agent': False}
        agent_options = {'bar': 'baz'}
        mock_bind_manager.consumer_bind_manager.return_value.get_bind.return_value = binding_config
        result = consumer.force_unbind('foo_consumer_id', 'foo_repo_id', 'foo_distributor_id',
                                       agent_options)

        mock_bind_manager.consumer_bind_manager.return_value.delete.assert_called_once_with(
            'foo_consumer_id', 'foo_repo_id', 'foo_distributor_id', True)

        self.assertEqual(result.error, None)
        self.assertEqual(result.return_value, None)
        self.assertEqual(result.spawned_tasks, [])

        #Make sure we didn't process the agent
        self.assertFalse(mock_bind_manager.consumer_agent_manager.called)

    @patch('pulp.server.tasks.consumer.managers')
    def test_unbind_with_agent_notification(self, mock_bind_manager):
        binding_config = {'notify_agent': True}
        agent_options = {'bar': 'baz'}
        mock_bind_manager.consumer_bind_manager.return_value.get_bind.return_value = binding_config
        mock_bind_manager.consumer_agent_manager.return_value.unbind.return_value = \
            {'task_id': 'foo-request-id', 'other_task_detail': 'abc123'}
        result = consumer.force_unbind('foo_consumer_id', 'foo_repo_id', 'foo_distributor_id',
                                       agent_options)
        mock_bind_manager.consumer_agent_manager.return_value.unbind.assert_called_once_with(
            'foo_consumer_id', 'foo_repo_id', 'foo_distributor_id', agent_options)
        self.assertTrue(isinstance(result, TaskResult))
        self.assertEquals(result.spawned_tasks, [{'task_id': 'foo-request-id'}])


class TestInstallContent(unittest.TestCase):

    @patch('pulp.server.tasks.consumer.managers')
    def test_install_content(self, mock_factory):
        # Setup
        mock_task = mock_factory.consumer_agent_manager.return_value.install_content
        mock_task.return_value = 'qux'
        result = consumer.install_content('foo', 'bar', 'baz')
        self.assertEquals('qux', result)
        mock_task.assert_called_once_with('foo', 'bar', 'baz')


class TestUpdateContent(unittest.TestCase):

    @patch('pulp.server.tasks.consumer.managers')
    def test_install_content(self, mock_factory):
        # Setup
        mock_task = mock_factory.consumer_agent_manager.return_value.update_content
        mock_task.return_value = 'qux'
        result = consumer.update_content('foo', 'bar', 'baz')
        self.assertEquals('qux', result)
        mock_task.assert_called_once_with('foo', 'bar', 'baz')


class TestUninstallContent(unittest.TestCase):

    @patch('pulp.server.tasks.consumer.managers')
    def test_install_content(self, mock_factory):
        # Setup
        mock_task = mock_factory.consumer_agent_manager.return_value.uninstall_content
        mock_task.return_value = 'qux'
        result = consumer.uninstall_content('foo', 'bar', 'baz')
        self.assertEquals('qux', result)
        mock_task.assert_called_once_with('foo', 'bar', 'baz')
