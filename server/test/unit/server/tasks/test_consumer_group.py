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
from pulp.server.exceptions import MissingResource, PulpException, error_codes
from pulp.server.tasks import consumer_group


class TestBind(unittest.TestCase):

    @patch('pulp.server.tasks.consumer_group.bind_task')
    @patch('pulp.server.managers.factory.consumer_group_query_manager')
    def test_bind_no_errors(self, mock_query_manager, mock_bind):
        mock_query_manager.return_value.get_group.return_value = {'consumer_ids': ['foo-consumer']}
        binding_config = {'binding': 'foo'}
        agent_options = {'bar': 'baz'}
        mock_bind.return_value = TaskResult(spawned_tasks=['foo-request-id'])
        result = consumer_group.bind('foo_group_id', 'foo_repo_id', 'foo_distributor_id',
                                     True, binding_config, agent_options)
        mock_bind.assert_called_once_with('foo-consumer', 'foo_repo_id', 'foo_distributor_id',
                                          True, binding_config, agent_options)
        self.assertEquals(result.spawned_tasks[0], 'foo-request-id')

    @patch('pulp.server.tasks.consumer_group.bind_task')
    @patch('pulp.server.managers.factory.consumer_group_query_manager')
    def test_bind_with_missing_resource_errors(self, mock_query_manager, mock_bind):
        mock_query_manager.return_value.get_group.return_value = {'consumer_ids': ['foo-consumer']}
        binding_config = {'binding': 'foo'}
        agent_options = {'bar': 'baz'}
        side_effect_exception = MissingResource()
        mock_bind.side_effect = side_effect_exception

        result = consumer_group.bind('foo_group_id', 'foo_repo_id', 'foo_distributor_id',
                                     True, binding_config, agent_options)
        self.assertTrue(isinstance(result.error, PulpException))
        self.assertEquals(result.error.error_code, error_codes.PLP0004)
        self.assertEquals(result.error.child_exceptions[0], side_effect_exception)

    @patch('pulp.server.tasks.consumer_group.bind_task')
    @patch('pulp.server.managers.factory.consumer_group_query_manager')
    def test_bind_with_general_error(self, mock_query_manager, mock_bind):
        mock_query_manager.return_value.get_group.return_value = {'consumer_ids': ['foo-consumer']}
        binding_config = {'binding': 'foo'}
        agent_options = {'bar': 'baz'}
        side_effect_exception = ValueError()
        mock_bind.side_effect = side_effect_exception

        result = consumer_group.bind('foo_group_id', 'foo_repo_id', 'foo_distributor_id',
                                     True, binding_config, agent_options)
        self.assertTrue(isinstance(result.error, PulpException))
        self.assertEquals(result.error.error_code, error_codes.PLP0004)
        self.assertEquals(result.error.child_exceptions[0], side_effect_exception)


class TestUnbind(unittest.TestCase):

    @patch('pulp.server.tasks.consumer_group.unbind_task')
    @patch('pulp.server.managers.factory.consumer_group_query_manager')
    def test_bind_no_errors(self, mock_query_manager, mock_unbind):
        mock_query_manager.return_value.get_group.return_value = {'consumer_ids': ['foo-consumer']}
        options = {'bar': 'baz'}
        mock_unbind.return_value = TaskResult(spawned_tasks=['foo-request-id'])
        result = consumer_group.unbind('foo_group_id', 'foo_repo_id', 'foo_distributor_id', options)
        mock_unbind.assert_called_once_with('foo-consumer', 'foo_repo_id', 'foo_distributor_id',
                                            options)
        self.assertEquals(result.spawned_tasks[0], 'foo-request-id')

    @patch('pulp.server.tasks.consumer_group.unbind_task')
    @patch('pulp.server.managers.factory.consumer_group_query_manager')
    def test_bind_with_missing_resource_errors(self, mock_query_manager, mock_unbind):
        mock_query_manager.return_value.get_group.return_value = {'consumer_ids': ['foo-consumer']}
        options = {'bar': 'baz'}
        side_effect_exception = MissingResource()
        mock_unbind.side_effect = side_effect_exception

        result = consumer_group.unbind('foo_group_id', 'foo_repo_id', 'foo_distributor_id', options)
        self.assertTrue(isinstance(result.error, PulpException))
        self.assertEquals(result.error.error_code, error_codes.PLP0005)
        self.assertEquals(result.error.child_exceptions[0], side_effect_exception)

    @patch('pulp.server.tasks.consumer_group.unbind_task')
    @patch('pulp.server.managers.factory.consumer_group_query_manager')
    def test_bind_with_general_error(self, mock_query_manager, mock_unbind):
        mock_query_manager.return_value.get_group.return_value = {'consumer_ids': ['foo-consumer']}
        options = {'bar': 'baz'}
        side_effect_exception = ValueError()
        mock_unbind.side_effect = side_effect_exception

        result = consumer_group.unbind('foo_group_id', 'foo_repo_id', 'foo_distributor_id', options)
        self.assertTrue(isinstance(result.error, PulpException))
        self.assertEquals(result.error.error_code, error_codes.PLP0005)
        self.assertEquals(result.error.child_exceptions[0], side_effect_exception)
