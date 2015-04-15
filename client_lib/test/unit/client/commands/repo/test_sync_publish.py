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
import unittest

import mock

from pulp.bindings import responses
from pulp.client.commands import options, polling
from pulp.client.commands.repo import sync_publish as sp
from pulp.client.extensions.core import TAG_TITLE
from pulp.client.extensions.extensions import PulpCliOption
from pulp.common import tags
from pulp.devel.unit import base


CALL_REPORT_TEMPLATE = {
    "exception": None,
    "task_id": 'default-id',
    "tags": ['pulp:action:sync'],
    "start_time": None,
    "traceback": None,
    "state": None,
    "finish_time": None,
    "schedule_id": None,
    "result": None,
    "progress_report": {},
}


class GetRepoTasksTests(unittest.TestCase):
    """
    Tests for the _get_repo_tasks() function.
    """
    def test_publish_action(self):
        """
        Test with action set to 'publish'.
        """
        context = mock.MagicMock()
        a_task = mock.MagicMock()
        context.server.tasks_search.search.return_value = [a_task]
        repo_id = 'some_repo'
        action = 'publish'

        tasks = sp._get_repo_tasks(context, repo_id, action)

        self.assertEqual(tasks, [a_task])
        expected_repo_tag = tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id)
        expected_action_tag = tags.action_tag(tags.ACTION_PUBLISH_TYPE)
        expected_search_criteria = {'filters': {'state': {'$nin': responses.COMPLETED_STATES},
                                                'tags': {'$all': [expected_repo_tag, expected_action_tag]}}}
        context.server.tasks_search.search.assert_called_once_with(**expected_search_criteria)

    def test_sync_action(self):
        """
        Test with action set to 'sync'.
        """
        context = mock.MagicMock()
        a_task = mock.MagicMock()
        context.server.tasks_search.search.return_value = [a_task]
        repo_id = 'some_repo'
        action = 'sync'

        tasks = sp._get_repo_tasks(context, repo_id, action)

        self.assertEqual(tasks, [a_task])
        expected_repo_tag = tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id)
        expected_action_tag = tags.action_tag(tags.ACTION_SYNC_TYPE)
        expected_search_criteria = {'filters': {'state': {'$nin': responses.COMPLETED_STATES},
                                                'tags': {'$all': [expected_repo_tag, expected_action_tag]}}}
        context.server.tasks_search.search.assert_called_once_with(**expected_search_criteria)

    def test_unsupported_action(self):
        """
        Test with action set to neither sync or publish.
        """
        context = mock.MagicMock()
        a_task = mock.MagicMock()
        context.server.tasks_search.search.return_value = [a_task]
        repo_id = 'some_repo'
        action = 'unsupported'

        self.assertRaises(ValueError, sp._get_repo_tasks, context, repo_id, action)


class SyncPublishCommandTests(base.PulpClientTests):
    """
    Tests for the SyncPublishCommand class.
    """
    @mock.patch('pulp.client.commands.polling.PollingCommand.__init__',
                side_effect=polling.PollingCommand.__init__, autospec=True)
    def test__init___method_set(self, __init__):
        """
        Test the __init__() method when method is set.
        """
        name = 'some_name'
        description = 'some_description'
        method = mock.MagicMock()
        context = mock.MagicMock()
        renderer = mock.MagicMock()

        spc = sp.SyncPublishCommand(name, description, method, context, renderer)

        self.assertEqual(spc.renderer, renderer)
        self.assertEqual(spc.context, context)
        self.assertEqual(spc.prompt, context.prompt)
        self.assertTrue(options.OPTION_REPO_ID in spc.options)
        __init__.assert_called_once_with(spc, name, description, method, context)

    @mock.patch('pulp.client.commands.polling.PollingCommand.__init__',
                side_effect=polling.PollingCommand.__init__, autospec=True)
    def test__init___method_unset(self, __init__):
        """
        Test the __init__() method when method is None.
        """
        name = 'some_name'
        description = 'some_description'
        method = None
        context = mock.MagicMock()
        renderer = mock.MagicMock()
        # Because the SyncPublishCommand does not have a run() method, we need to make and test a subclass of
        # it that has a run() method to ensure that method defaults to run() when is is None.
        class TestSubclass(sp.SyncPublishCommand):
            def run(self):
                pass

        spc = TestSubclass(name, description, method, context, renderer)

        self.assertEqual(spc.renderer, renderer)
        self.assertEqual(spc.context, context)
        self.assertEqual(spc.prompt, context.prompt)
        self.assertTrue(options.OPTION_REPO_ID in spc.options)
        # When method is None, self.run should have been used instead
        __init__.assert_called_once_with(spc, name, description, spc.run, context)


class RunSyncRepositoryCommandTests(base.PulpClientTests):
    """
    Test the RunSyncRepositoryCommand class.
    """
    def setUp(self):
        super(RunSyncRepositoryCommandTests, self).setUp()
        self.mock_renderer = mock.MagicMock()
        self.command = sp.RunSyncRepositoryCommand(self.context, self.mock_renderer)

    def test_progress(self):
        """
        Test the progress() method with a progress_report.
        """
        progress_report = {'some': 'data'}
        task = responses.Task({'progress_report': progress_report})
        spinner = mock.MagicMock()

        self.command.progress(task, spinner)

        self.mock_renderer.display_report.assert_called_once_with(progress_report)

    def test_progress_no_progress(self):
        """
        Test the progress() method when the Task does not have any progress_report.
        """
        task = responses.Task({})
        spinner = mock.MagicMock()

        self.command.progress(task, spinner)

        self.assertEqual(self.mock_renderer.display_report.call_count, 0)

    def test_structure(self):
        # Ensure all of the expected options are there
        found_option_keywords = set([o.keyword for o in self.command.options])
        expected_option_keywords = set([options.OPTION_REPO_ID.keyword, polling.FLAG_BACKGROUND.keyword])
        self.assertEqual(found_option_keywords, expected_option_keywords)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'run')
        self.assertEqual(self.command.description, sp.DESC_SYNC_RUN)

    @mock.patch('pulp.client.commands.repo.sync_publish.RunSyncRepositoryCommand.poll')
    @mock.patch('pulp.bindings.tasks.TaskSearchAPI.search')
    @mock.patch('pulp.bindings.repository.RepositoryActionsAPI.sync')
    def test_run(self, mock_sync, mock_search, poll):
        """
        Test the run() method when there is not an existing sync Task on the server.
        """
        repo_id = 'test-repo'
        data = {options.OPTION_REPO_ID.keyword : repo_id, polling.FLAG_BACKGROUND.keyword: False}
        # No tasks are running
        mock_search.return_value = []
        # responses.Response from the sync call
        task_data = copy.copy(CALL_REPORT_TEMPLATE)
        task = responses.Task(task_data)
        mock_sync.return_value = responses.Response(202, task)

        self.command.run(**data)

        mock_sync.assert_called_once_with(repo_id, None)
        sync_tasks = poll.mock_calls[0][1][0]
        poll.assert_called_once_with(sync_tasks, data)
        expected_search_query = {
            'state': {'$nin': responses.COMPLETED_STATES},
            'tags': {'$all': [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                              tags.action_tag(tags.ACTION_SYNC_TYPE)]}}
        mock_search.assert_called_once_with(filters=expected_search_query)
        self.assertEqual(self.prompt.get_write_tags(), [TAG_TITLE])

    @mock.patch('pulp.client.commands.repo.sync_publish.RunSyncRepositoryCommand.poll')
    @mock.patch('pulp.bindings.tasks.TaskSearchAPI.search')
    @mock.patch('pulp.bindings.repository.RepositoryActionsAPI.sync')
    def test_run_already_in_progress(self, mock_sync, mock_search, poll):
        """
        Test the run() method when there is an existing sync Task on the server.
        """
        repo_id = 'test-repo'
        data = {options.OPTION_REPO_ID.keyword : repo_id, polling.FLAG_BACKGROUND.keyword: False}
        # Simulate a task already running
        task_data = copy.copy(CALL_REPORT_TEMPLATE)
        task_data['state'] = 'running'
        task = responses.Task(task_data)
        mock_search.return_value = [task]

        self.command.run(**data)

        self.assertEqual(mock_sync.call_count, 0)
        sync_tasks = poll.mock_calls[0][1][0]
        expected_search_query = {
            'state': {'$nin': responses.COMPLETED_STATES},
            'tags': {'$all': [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                              tags.action_tag(tags.ACTION_SYNC_TYPE)]}}
        mock_search.assert_called_once_with(filters=expected_search_query)
        poll.assert_called_once_with(sync_tasks, data)
        write_tags = self.prompt.get_write_tags()
        self.assertEqual(2, len(write_tags))
        self.assertEqual(write_tags[1], 'in-progress')

    @mock.patch('pulp.client.commands.repo.sync_publish.RunSyncRepositoryCommand.poll')
    @mock.patch('pulp.bindings.tasks.TaskSearchAPI.search')
    @mock.patch('pulp.bindings.repository.RepositoryActionsAPI.sync')
    def test_run_background(self, mock_sync, mock_search, mock_poll):
        """
        Test the run() method when the --bg flag is set.
        """
        repo_id = 'test-repo'
        data = {options.OPTION_REPO_ID.keyword : repo_id, polling.FLAG_BACKGROUND.keyword: True}
        # No tasks are running
        mock_search.return_value = []
        # responses.Response from the sync call
        task_data = copy.copy(CALL_REPORT_TEMPLATE)
        task = responses.Task(task_data)
        mock_sync.return_value = responses.Response(202, task)

        self.command.run(**data)

        mock_sync.assert_called_once_with(repo_id, None)
        expected_search_query = {
            'state': {'$nin': responses.COMPLETED_STATES},
            'tags': {'$all': [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                              tags.action_tag(tags.ACTION_SYNC_TYPE)]}}
        mock_search.assert_called_once_with(filters=expected_search_query)
        mock_poll.assert_called_once_with([task], data)

    def test_task_header(self):
        """
        The task_header() method only passes to avoid the superclass's behavior, so this test just gets us to
        100% coverage.
        """
        self.command.task_header(mock.MagicMock())


class SyncStatusCommand(base.PulpClientTests):
    def setUp(self):
        super(SyncStatusCommand, self).setUp()
        self.renderer = mock.MagicMock()
        self.command = sp.SyncStatusCommand(self.context, self.renderer)

    def test_structure(self):
        # Ensure all of the expected options are there
        found_options = set(self.command.options)
        expected_options = set([options.OPTION_REPO_ID, polling.FLAG_BACKGROUND])
        self.assertEqual(found_options, expected_options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'status')
        self.assertEqual(self.command.description, sp.DESC_SYNC_STATUS)

    @mock.patch('pulp.client.commands.repo.sync_publish.SyncStatusCommand.poll')
    @mock.patch('pulp.bindings.tasks.TaskSearchAPI.search')
    def test_run(self, mock_search, poll):
        """
        Test the run() method when the server has one incomplete sync task.
        """
        repo_id = 'test-repo'
        data = {options.OPTION_REPO_ID.keyword: repo_id}
        task_data = copy.copy(CALL_REPORT_TEMPLATE)
        task_data['state'] = 'running'
        task = responses.Task(task_data)
        mock_search.return_value = [task]

        self.command.run(**data)

        expected_search_query = {
            'state': {'$nin': responses.COMPLETED_STATES},
            'tags': {'$all': [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                              tags.action_tag(tags.ACTION_SYNC_TYPE)]}}
        mock_search.assert_called_once_with(filters=expected_search_query)
        sync_tasks = poll.mock_calls[0][1][0]
        poll.assert_called_once_with(sync_tasks, data)

    @mock.patch('pulp.client.commands.repo.sync_publish.PublishStatusCommand.poll')
    @mock.patch('pulp.bindings.tasks.TaskSearchAPI.search')
    def test_run_no_status(self, mock_search, mock_poll):
        """
        Test run() when there are no sync_tasks on the server.
        """
        repo_id = 'test-repo'
        data = {options.OPTION_REPO_ID.keyword: repo_id}
        # No tasks are running
        mock_search.return_value = []

        self.command.run(**data)

        expected_search_query = {
            'state': {'$nin': responses.COMPLETED_STATES},
            'tags': {'$all': [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                              tags.action_tag(tags.ACTION_SYNC_TYPE)]}}
        mock_search.assert_called_once_with(filters=expected_search_query)
        self.assertEqual(0, mock_poll.call_count)
        self.assertEqual(self.prompt.get_write_tags(), [TAG_TITLE, 'no-tasks'])


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

        expected_option_keywords = set([options.OPTION_REPO_ID.keyword, polling.FLAG_BACKGROUND.keyword])
        expected_group_option_keywords = set([self.sample_option1.keyword, self.sample_option2.keyword])

        self.assertEqual(found_option_keywords, expected_option_keywords)
        self.assertEqual(found_group_option_keywords, expected_group_option_keywords)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'run')
        self.assertEqual(self.command.description, sp.DESC_PUBLISH_RUN)

    @mock.patch('pulp.client.commands.repo.sync_publish.RunPublishRepositoryCommand.poll')
    @mock.patch('pulp.bindings.tasks.TaskSearchAPI.search')
    @mock.patch('pulp.bindings.repository.RepositoryActionsAPI.publish')
    def test_run(self, mock_publish, mock_search, mock_poll):
        """
        Test the run() method when there are no incomplete publish tasks in queue.
        """
        repo_id = 'test-repo'
        data = {options.OPTION_REPO_ID.keyword: repo_id, polling.FLAG_BACKGROUND.keyword: False}
        # No tasks are running
        mock_search.return_value = []
        # responses.Response from the sync call
        task_data = copy.copy(CALL_REPORT_TEMPLATE)
        task = responses.Task(task_data)
        mock_publish.return_value = responses.Response(202, task)

        self.command.run(**data)

        mock_publish.assert_called_once_with(repo_id, self.command.distributor_id, None)
        expected_search_query = {
            'state': {'$nin': responses.COMPLETED_STATES},
            'tags': {'$all': [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                              tags.action_tag(tags.ACTION_PUBLISH_TYPE)]}}
        mock_search.assert_called_once_with(filters=expected_search_query)
        mock_poll.assert_called_once_with([task], data)

    @mock.patch('pulp.client.commands.repo.sync_publish.RunPublishRepositoryCommand.poll')
    @mock.patch('pulp.bindings.tasks.TaskSearchAPI.search')
    @mock.patch('pulp.bindings.repository.RepositoryActionsAPI.publish')
    def test_run_already_in_progress(self, mock_publish, mock_search, mock_poll):
        """
        Test the run() method when thre is already an incomplete publish operation.
        """
        repo_id = 'test-repo'
        data = {options.OPTION_REPO_ID.keyword: repo_id, polling.FLAG_BACKGROUND.keyword: False}
        # Simulate a task already running
        task_data = copy.copy(CALL_REPORT_TEMPLATE)
        task_data['state'] = 'running'
        task = responses.Task(task_data)
        mock_search.return_value = [task]

        self.command.run(**data)

        # Publish shouldn't get called again since it's already running
        self.assertEqual(mock_publish.call_count, 0)
        expected_search_query = {
            'state': {'$nin': responses.COMPLETED_STATES},
            'tags': {'$all': [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                              tags.action_tag(tags.ACTION_PUBLISH_TYPE)]}}
        mock_search.assert_called_once_with(filters=expected_search_query)
        mock_poll.assert_called_once_with([task], data)
        write_tags = self.prompt.get_write_tags()
        self.assertEqual(2, len(write_tags))
        self.assertEqual(write_tags[1], 'in-progress')

    @mock.patch('pulp.client.commands.repo.sync_publish.RunPublishRepositoryCommand.poll')
    @mock.patch('pulp.bindings.tasks.TaskSearchAPI.search')
    @mock.patch('pulp.bindings.repository.RepositoryActionsAPI.publish')
    def test_run_background(self, mock_publish, mock_search, mock_poll):
        """
        Test run() with the --bg flag is set.
        """
        repo_id = 'test-repo'
        data = {options.OPTION_REPO_ID.keyword: repo_id, polling.FLAG_BACKGROUND.keyword: False}
        # No tasks are running
        mock_search.return_value = []
        # responses.Response from the sync call
        task_data = copy.copy(CALL_REPORT_TEMPLATE)
        task = responses.Task(task_data)
        mock_publish.return_value = responses.Response(202, task)

        self.command.run(**data)

        mock_publish.assert_called_once_with(repo_id, self.command.distributor_id, None)
        expected_search_query = {
            'state': {'$nin': responses.COMPLETED_STATES},
            'tags': {'$all': [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                              tags.action_tag(tags.ACTION_PUBLISH_TYPE)]}}
        mock_search.assert_called_once_with(filters=expected_search_query)
        mock_poll.assert_called_once_with([task], data)


class PublishStatusCommand(base.PulpClientTests):
    def setUp(self):
        super(PublishStatusCommand, self).setUp()
        self.renderer = mock.MagicMock()
        self.command = sp.PublishStatusCommand(self.context, self.renderer)

    def test_structure(self):
        # Ensure all of the expected options are there
        found_options = set(self.command.options)
        expected_options = set([options.OPTION_REPO_ID, polling.FLAG_BACKGROUND])
        self.assertEqual(found_options, expected_options)

        # Ensure the correct method is wired up
        self.assertEqual(self.command.method, self.command.run)

        # Ensure the correct metadata
        self.assertEqual(self.command.name, 'status')
        self.assertEqual(self.command.description, sp.DESC_PUBLISH_STATUS)

    @mock.patch('pulp.client.commands.repo.sync_publish.PublishStatusCommand.poll')
    @mock.patch('pulp.bindings.tasks.TaskSearchAPI.search')
    def test_run(self, mock_search, mock_poll):
        """
        Test the run() method when there is one publish Task. It should call poll() on it.
        """
        repo_id = 'test-repo'
        data = {options.OPTION_REPO_ID.keyword: repo_id}
        # Simulate a task already running
        task_data = copy.copy(CALL_REPORT_TEMPLATE)
        task_data['state'] = 'running'
        task = responses.Task(task_data)
        mock_search.return_value = [task]

        self.command.run(**data)

        expected_search_query = {
            'state': {'$nin': responses.COMPLETED_STATES},
            'tags': {'$all': [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                              tags.action_tag(tags.ACTION_PUBLISH_TYPE)]}}
        mock_search.assert_called_once_with(filters=expected_search_query)
        mock_poll.assert_called_once_with([task], data)

    @mock.patch('pulp.client.commands.repo.sync_publish.PublishStatusCommand.poll')
    @mock.patch('pulp.bindings.tasks.TaskSearchAPI.search')
    def test_run_no_status(self, mock_search, mock_poll):
        """
        Test the run() method when there are no current publish Tasks to attach to. It
        should query the server and inform the user that there are no publish operations to
        report.
        """
        repo_id = 'test-repo'
        data = {options.OPTION_REPO_ID.keyword: repo_id}
        # Simulate there being no publish tasks
        mock_search.return_value = []

        self.command.run(**data)

        expected_search_query = {
            'state': {'$nin': responses.COMPLETED_STATES},
            'tags': {'$all': [tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
                              tags.action_tag(tags.ACTION_PUBLISH_TYPE)]}}
        mock_search.assert_called_once_with(filters=expected_search_query)
        self.assertEqual(0, mock_poll.call_count)
        self.assertEqual(self.prompt.get_write_tags(), [TAG_TITLE, 'no-tasks'])
