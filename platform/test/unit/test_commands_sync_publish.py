# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Testing this stuff is a nightmare. To ease the pain, these tests only cover the
commands themselves and ensure they call into the status rendering module. The
status module itself will be tested apart from what happens in the commands.
"""

import copy
import mock
import unittest

import base

from pulp.bindings.responses import Response, Task
from pulp.client.commands import options
from pulp.client.commands.repo import sync_publish as sp

from pulp.client.extensions.extensions import PulpCliOption


CALL_REPORT_TEMPLATE = {
    "exception": None,
    "task_group_id": 'default-group',
    "task_id": 'default-id',
    "tags": ['pulp:action:sync'],
    "reasons": [],
    "start_time": None,
    "traceback": None,
    "state": None,
    "finish_time": None,
    "schedule_id": None,
    "result": None,
    "progress": {},
    "response": None,
}

# -- test cases ---------------------------------------------------------------

class RunSyncRepositoryCommandTests(base.PulpClientTests):

    def setUp(self):
        super(RunSyncRepositoryCommandTests, self).setUp()
        self.mock_renderer = mock.MagicMock()
        self.command = sp.RunSyncRepositoryCommand(self.context, self.mock_renderer)

    def test_structure(self):
        # Ensure all of the expected options are there
        found_option_keywords = set([o.keyword for o in self.command.options])
        expected_option_keywords = set([options.OPTION_REPO_ID.keyword, sp.NAME_BACKGROUND])
        self.assertEqual(found_option_keywords, expected_option_keywords)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'run')
        self.assertEqual(self.command.description, sp.DESC_SYNC_RUN)

    @mock.patch('pulp.client.commands.repo.status.status.display_group_status')
    @mock.patch('pulp.bindings.tasks.TasksAPI.get_repo_sync_tasks')
    @mock.patch('pulp.bindings.repository.RepositoryActionsAPI.sync')
    def test_run(self, mock_sync, mock_get, mock_status):
        # Setup
        data = {
            options.OPTION_REPO_ID.keyword : 'test-repo',
            sp.NAME_BACKGROUND : False,
        }

        # No tasks are running
        mock_get.return_value = Response(200, [])

        # Response from the sync call
        task_data = copy.copy(CALL_REPORT_TEMPLATE)
        task = Task(task_data)
        mock_sync.return_value = Response(202, [task])

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, mock_status.call_count)

    @mock.patch('pulp.client.commands.repo.status.status.display_group_status')
    @mock.patch('pulp.bindings.tasks.TasksAPI.get_repo_sync_tasks')
    @mock.patch('pulp.bindings.repository.RepositoryActionsAPI.sync')
    def test_run_already_in_progress(self, mock_sync, mock_get, mock_status):
        # Setup
        data = {
            options.OPTION_REPO_ID.keyword : 'test-repo',
            sp.NAME_BACKGROUND : False,
        }

        # Simulate a task already running
        task_data = copy.copy(CALL_REPORT_TEMPLATE)
        task_data['response'] = 'accepted'
        task_data['state'] = 'running'
        task = Task(task_data)
        mock_get.return_value = Response(200, [task])

        # Response from the sync call
        task_data = copy.copy(CALL_REPORT_TEMPLATE)
        task = Task(task_data)
        mock_sync.return_value = Response(202, [task])

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, mock_status.call_count)

        tags = self.prompt.get_write_tags()
        self.assertEqual(2, len(tags))
        self.assertEqual(tags[1], 'in-progress')

    @mock.patch('pulp.client.commands.repo.status.status.display_group_status')
    @mock.patch('pulp.bindings.tasks.TasksAPI.get_repo_sync_tasks')
    @mock.patch('pulp.bindings.repository.RepositoryActionsAPI.sync')
    def test_run_background(self, mock_sync, mock_get, mock_status):
        # Setup
        data = {
            options.OPTION_REPO_ID.keyword : 'test-repo',
            sp.NAME_BACKGROUND : True,
        }

        # No tasks are running
        mock_get.return_value = Response(200, [])

        # Response from the sync call
        task_data = copy.copy(CALL_REPORT_TEMPLATE)
        task = Task(task_data)
        mock_sync.return_value = Response(202, [task])

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(0, mock_status.call_count) # since its background

        tags = self.prompt.get_write_tags()
        self.assertEqual(2, len(tags))
        self.assertEqual(tags[1], 'background')


class SyncStatusCommand(base.PulpClientTests):
    def setUp(self):
        super(SyncStatusCommand, self).setUp()
        self.renderer = mock.MagicMock()
        self.command = sp.SyncStatusCommand(self.context, self.renderer)

    def test_structure(self):
        # Ensure all of the expected options are there
        found_options = set(self.command.options)
        expected_options = set([options.OPTION_REPO_ID])
        self.assertEqual(found_options, expected_options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'status')
        self.assertEqual(self.command.description, sp.DESC_SYNC_STATUS)

    def test_run(self):
        # Make sure it doesn't raise an exception
        self.command.run()


class StatusRendererTests(unittest.TestCase):

    def test_default_display_report(self):
        # Setup
        mock_context = mock.MagicMock()
        mock_prompt = mock.MagicMock()
        mock_context.prompt = mock_prompt

        # Test
        sr = sp.StatusRenderer(mock_context)
        self.assertRaises(NotImplementedError, sr.display_report, None)

        # Verify
        self.assertTrue(sr.context is mock_context)
        self.assertTrue(sr.prompt is mock_prompt)
        
        
class RunPublishRepositoryCommandTests(base.PulpClientTests):

    def setUp(self):
        super(RunPublishRepositoryCommandTests, self).setUp()
        self.mock_renderer = mock.MagicMock()
        self.command = sp.RunPublishRepositoryCommand(self.context, self.mock_renderer, distributor_id='yum_distributor')
        self.sample_option1 = PulpCliOption('--sample-option1', "sample_option1", required=False)
        self.sample_option2 = PulpCliOption('--sample-option2', "sample_option2", required=False)
        self.additional_publish_options = [self.sample_option1, self.sample_option2]

    def test_structure(self):
        # Ensure all of the expected options are there
        self.command = sp.RunPublishRepositoryCommand(self.context, self.mock_renderer, distributor_id='yum_distributor',
                                                      override_config_options=self.additional_publish_options)
        found_option_keywords = set([o.keyword for o in self.command.options])
        found_group_option_keywords = set([o.keyword for o in self.command.option_groups[0].options])

        expected_option_keywords = set([options.OPTION_REPO_ID.keyword, sp.NAME_BACKGROUND])
        expected_group_option_keywords = set([self.sample_option1.keyword, self.sample_option2.keyword])

        self.assertEqual(found_option_keywords, expected_option_keywords)
        self.assertEqual(found_group_option_keywords, expected_group_option_keywords)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'run')
        self.assertEqual(self.command.description, sp.DESC_PUBLISH_RUN)

    @mock.patch('pulp.client.commands.repo.status.status.display_task_status')
    @mock.patch('pulp.bindings.tasks.TasksAPI.get_repo_publish_tasks')
    @mock.patch('pulp.bindings.repository.RepositoryActionsAPI.publish')
    def test_run(self, mock_publish, mock_get, mock_status):
        # Setup
        data = {
            options.OPTION_REPO_ID.keyword : 'test-repo',
            sp.NAME_BACKGROUND : False,
        }

        # No tasks are running
        mock_get.return_value = Response(200, [])

        # Response from the sync call
        task_data = copy.copy(CALL_REPORT_TEMPLATE)
        task = Task(task_data)
        mock_publish.return_value = Response(202, task)

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, mock_status.call_count)

    @mock.patch('pulp.client.commands.repo.status.status.display_task_status')
    @mock.patch('pulp.bindings.tasks.TasksAPI.get_repo_publish_tasks')
    @mock.patch('pulp.bindings.repository.RepositoryActionsAPI.publish')
    def test_run_already_in_progress(self, mock_publish, mock_get, mock_status):
        # Setup
        data = {
            options.OPTION_REPO_ID.keyword : 'test-repo',
            sp.NAME_BACKGROUND : False,
        }

        # Simulate a task already running
        task_data = copy.copy(CALL_REPORT_TEMPLATE)
        task_data['response'] = 'accepted'
        task_data['state'] = 'running'
        task = Task(task_data)
        mock_get.return_value = Response(200, [task])

        # Response from the sync call
        task_data = copy.copy(CALL_REPORT_TEMPLATE)
        task = Task(task_data)
        mock_publish.return_value = Response(202, task)

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(1, mock_status.call_count)

        tags = self.prompt.get_write_tags()
        self.assertEqual(2, len(tags))
        self.assertEqual(tags[1], 'in-progress')

    @mock.patch('pulp.client.commands.repo.status.status.display_task_status')
    @mock.patch('pulp.bindings.tasks.TasksAPI.get_repo_publish_tasks')
    @mock.patch('pulp.bindings.repository.RepositoryActionsAPI.publish')
    def test_run_background(self, mock_publish, mock_get, mock_status):
        # Setup
        data = {
            options.OPTION_REPO_ID.keyword : 'test-repo',
            sp.NAME_BACKGROUND : True,
        }

        # No tasks are running
        mock_get.return_value = Response(200, [])

        # Response from the sync call
        task_data = copy.copy(CALL_REPORT_TEMPLATE)
        task = Task(task_data)
        mock_publish.return_value = Response(202, task)

        # Test
        self.command.run(**data)

        # Verify
        self.assertEqual(0, mock_status.call_count) # since its background

        tags = self.prompt.get_write_tags()
        self.assertEqual(2, len(tags))
        self.assertEqual(tags[1], 'background')

