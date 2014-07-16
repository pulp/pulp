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
from datetime import datetime

import mock

from pulp.bindings import responses
from pulp.client.commands import options, polling
from pulp.client.commands.repo import sync_publish as sp
from pulp.client.extensions.core import TAG_TITLE, ClientContext, PulpPrompt
from pulp.client.extensions.extensions import PulpCliOption
from pulp.common import tags
from pulp.common.plugins import progress
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


class TestSyncStatusReport(unittest.TestCase):
    """
    Originally from test_extension_admin_iso_status.py in pulp_rpm
    """

    def setUp(self):
        self.context = mock.MagicMock(spec=ClientContext)
        self.context.prompt = mock.MagicMock(spec=PulpPrompt)

    def test___init__(self):
        """
        Test the SyncStatusRenderer.__init__() method.
        """
        renderer = sp.SyncStatusRenderer(self.context)

        self.assertEqual(renderer._sync_state, progress.SyncProgressReport.STATE_NOT_STARTED)
        self.context.prompt.create_progress_bar.assert_called_once_with()

    def test__display_sync_report_during_complete_stage(self):
        """
        Test the SyncStatusRenderer._display_sync_report method when the
        SyncProgressReport has entered the COMPLETE state (with three files
        successfully downloaded). It should display completion progress to the user.
        """
        conduit = mock.MagicMock()
        finished_bytes = 1204
        total_bytes = 1204
        state_times = {progress.SyncProgressReport.STATE_MANIFEST_IN_PROGRESS: datetime.utcnow()}
        sync_report = progress.SyncProgressReport(
            conduit, num_files=3, num_files_finished=3, total_bytes=total_bytes,
            finished_bytes=finished_bytes, state=progress.SyncProgressReport.STATE_COMPLETE,
            state_times=state_times)
        renderer = sp.SyncStatusRenderer(self.context)
        # Let's put the renderer in the manifest retrieval stage, simulating
        # the SyncProgressReport having just left that stage
        renderer._sync_state = progress.SyncProgressReport.STATE_MANIFEST_IN_PROGRESS
        renderer.prompt.reset_mock()

        # pretend we are downloading something called "chickens"
        renderer._display_sync_report(sync_report, "chickens")

        renderer.prompt.write.assert_has_call('Downloading 3 chickens.')
        # The _sync_state should have been updated to reflect the file
        # downloading stage being complete
        self.assertEqual(renderer._sync_state, progress.SyncProgressReport.STATE_COMPLETE)
        # A progress bar should have been rendered
        self.assertEqual(renderer._sync_files_bar.render.call_count, 1)
        args = renderer._sync_files_bar.render.mock_calls[0][1]
        self.assertEqual(args[0], finished_bytes)
        self.assertEqual(args[1], total_bytes)

        # There should be one kwarg - message. It is non-deterministic, so
        # let's just assert that it has some of the right text in it
        kwargs = renderer._sync_files_bar.render.mock_calls[0][2]
        self.assertEqual(len(kwargs), 1)
        self.assertTrue('chickens: 3/3' in kwargs['message'])

        # A completion message should have been printed for the user
        self.assertEqual(renderer.prompt.render_success_message.mock_calls[0][2]['tag'],
                         'download_success')

    def test__display_sync_report_during_files_failed_state(self):
        """
        Test the SyncStatusRenderer._display_sync_report method when the SyncProgressReport has
        entered STATE_FILES_FAILED (with two files successfully downloaded). It should display an
        error message to the user.
        """
        conduit = mock.MagicMock()
        finished_bytes = 1204
        total_bytes = 908
        files_error_messages = [
            {'name': 'bad.files', 'error': 'Sorry, I will not tell you what happened.'}]
        state_times = {progress.SyncProgressReport.STATE_MANIFEST_IN_PROGRESS: datetime.utcnow()}
        sync_report = progress.SyncProgressReport(
            conduit, num_files=3, num_files_finished=2, total_bytes=total_bytes,
            finished_bytes=finished_bytes, state=progress.SyncProgressReport.STATE_FILES_FAILED,
            state_times=state_times, files_error_messages=files_error_messages)
        renderer = sp.SyncStatusRenderer(self.context)
        # Let's put the renderer in the manifest retrieval stage, simulating the SyncProgressReport
        # having just left that stage
        renderer._sync_state = progress.SyncProgressReport.STATE_MANIFEST_IN_PROGRESS
        renderer.prompt.reset_mock()

        renderer._display_sync_report(sync_report, "Turkeys")

        renderer.prompt.write.assert_has_call('Downloading 3 Turkeys.')
        # The _sync_state should have been updated to reflect the file downloading stage having
        # failed
        self.assertEqual(renderer._sync_state, progress.SyncProgressReport.STATE_FILES_FAILED)
        # A progress bar should have been rendered
        self.assertEqual(renderer._sync_files_bar.render.call_count, 1)
        args = renderer._sync_files_bar.render.mock_calls[0][1]
        self.assertEqual(args[0], finished_bytes)
        self.assertEqual(args[1], total_bytes)

        # There should be one kwarg - message. It is non-deterministic, so let's just assert that it
        # has some of the right text in it
        kwargs = renderer._sync_files_bar.render.mock_calls[0][2]
        self.assertEqual(len(kwargs), 1)
        self.assertTrue('Turkeys: 2/3' in kwargs['message'])

        # A completion message should have been printed for the user
        self.assertEqual(renderer.prompt.render_failure_message.mock_calls[0][2]['tag'],
                         'download_failed')

        # The individual file that failed should have had its error message printed to screen
        self.assertTrue(files_error_messages[0]['error'] in
                        renderer.prompt.render_failure_message.mock_calls[1][1][0])
        self.assertEqual(renderer.prompt.render_failure_message.mock_calls[1][2]['tag'],
                         'file_error_msg')

    def test__display_sync_report_during_file_stage_no_files(self):
        """
        Test the SyncStatusRenderer._display_sync_report method when the
        SyncProgressReport has entered the file retrieval stage (with no files to
        download) from the manifest retrieval stage. It should just tell the user there
        is nothing to do.
        """
        conduit = mock.MagicMock()
        sync_report = progress.SyncProgressReport(
            conduit, num_files=0, state=progress.SyncProgressReport.STATE_FILES_IN_PROGRESS)
        renderer = sp.SyncStatusRenderer(self.context)
        # Let's put the renderer in the manifest retrieval stage, simulating
        # the SyncProgressReport having just left that stage
        renderer._sync_state = progress.SyncProgressReport.STATE_MANIFEST_IN_PROGRESS
        renderer.prompt.reset_mock()

        renderer._display_sync_report(sync_report, "penguins")

        self.assertEqual(renderer.prompt.render_success_message.call_count, 1)
        self.assertTrue('no penguins' in renderer.prompt.render_success_message.mock_calls[0][1][0])
        self.assertEqual(renderer.prompt.render_success_message.mock_calls[0][2]['tag'],
                         'none_to_download')
        # The _sync_state should have been updated to reflect the file
        # downloading stage being complete
        self.assertEqual(renderer._sync_state, progress.SyncProgressReport.STATE_COMPLETE)

    def test__display_sync_report_during_file_stage_with_files(self):
        """
        Test the SyncStatusRenderer._display_sync_report method when the
        SyncProgressReport has entered the file retrieval stage (with three files to
        download) from the manifest retrieval stage. It should display progress to the
        user.
        """
        conduit = mock.MagicMock()
        finished_bytes = 12
        total_bytes = 1204
        state_times = {progress.SyncProgressReport.STATE_MANIFEST_IN_PROGRESS: datetime.utcnow()}
        sync_report = progress.SyncProgressReport(
            conduit, num_files=3, total_bytes=total_bytes, finished_bytes=finished_bytes,
            state=progress.SyncProgressReport.STATE_FILES_IN_PROGRESS, state_times=state_times)
        renderer = sp.SyncStatusRenderer(self.context)
        # Let's put the renderer in the manifest retrieval stage, simulating
        # the SyncProgressReport having just left that stage
        renderer._sync_state = progress.SyncProgressReport.STATE_MANIFEST_IN_PROGRESS
        renderer.prompt.reset_mock()

        renderer._display_sync_report(sync_report, "emus")

        # The user should be informed that downloading is starting for three files
        self.assertEqual(renderer.prompt.write.call_count, 1)
        self.assertEqual(renderer.prompt.write.mock_calls[0][2]['tag'], 'download_starting')

        # The _sync_state should have been updated to reflect the file
        # downloading stage being in progress
        self.assertEqual(renderer._sync_state, progress.SyncProgressReport.STATE_FILES_IN_PROGRESS)
        # A progress bar should have been rendered
        self.assertEqual(renderer._sync_files_bar.render.call_count, 1)
        args = renderer._sync_files_bar.render.mock_calls[0][1]
        self.assertEqual(args[0], finished_bytes)
        self.assertEqual(args[1], total_bytes)

        # There should be one kwarg - message. It is non-deterministic, so
        # let's just assert that it has some of the right text in it
        kwargs = renderer._sync_files_bar.render.mock_calls[0][2]
        self.assertEqual(len(kwargs), 1)
        self.assertTrue('emus: 0/3' in kwargs['message'])

    def test__display_sync_report_during_manifest_stage(self):
        """
        Test the SyncStatusRenderer._display_sync_report method when the
        SyncProgressReport is in the manifest retrieval stage. It should not display
        anything to the user.
        """
        conduit = mock.MagicMock()
        sync_report = progress.SyncProgressReport(conduit,
                                                  state=progress.SyncProgressReport.
                                                  STATE_MANIFEST_IN_PROGRESS)
        renderer = sp.SyncStatusRenderer(self.context)
        # Let's also put the renderer in the manifest retrieval stage
        renderer._sync_state = progress.SyncProgressReport.STATE_MANIFEST_IN_PROGRESS
        renderer.prompt.reset_mock()

        renderer._display_sync_report(sync_report, "crows")

        # Because we are in the manifest state, this method should not do anything with the prompt
        self.assertEqual(renderer.prompt.mock_calls, [])

    def test__display_manifest_sync_report_manifest_complete(self):
        """
        Test behavior from _display_manifest_sync_report when the manifest is complete.
        """
        sync_report = progress.SyncProgressReport(None,
                                                  state=progress.SyncProgressReport.
                                                  STATE_FILES_IN_PROGRESS)
        renderer = sp.SyncStatusRenderer(self.context)
        # Let's also put the renderer in the manifest retrieval stage
        renderer._sync_state = progress.SyncProgressReport.STATE_NOT_STARTED
        renderer.prompt.reset_mock()

        renderer._display_manifest_sync_report(sync_report, "ostrich manifest")

        # There should be one message printed to the user that tells them the manifest is complete
        self.assertEqual(len(renderer.prompt.mock_calls), 1)
        self.assertEqual(renderer.prompt.mock_calls[0][2]['tag'], 'manifest_downloaded')
        # The renderer state should have been advanced to
        # STATE_MANIFEST_IN_PROGRESS, but not beyond, as _display_sync_report
        # will move it into the next state
        self.assertEqual(renderer._sync_state,
                         progress.SyncProgressReport.STATE_MANIFEST_IN_PROGRESS)

    def test__display_manifest_sync_report_manifest_failed(self):
        """
        Test behavior from _display_manifest_sync_report when the manifest failed to be retrieved.
        """
        conduit = mock.MagicMock()
        error_message = 'It broke.'
        sync_report = progress.SyncProgressReport(conduit, error_message=error_message,
                                                  state=progress.SyncProgressReport.
                                                  STATE_MANIFEST_FAILED)
        renderer = sp.SyncStatusRenderer(self.context)
        # Let's also put the renderer in the manifest retrieval stage
        renderer._sync_state = progress.SyncProgressReport.STATE_NOT_STARTED
        renderer.prompt.reset_mock()

        renderer._display_manifest_sync_report(sync_report, "duck manifest")

        # There should be two calls to mock. One to report the manifest
        # failure, and one to report the reason.
        self.assertEqual(len(renderer.prompt.mock_calls), 2)
        self.assertEqual(renderer.prompt.mock_calls[0][2]['tag'], 'manifest_failed')

        # Make sure we told the user the error message
        self.assertEqual(renderer.prompt.mock_calls[1][2]['tag'], 'manifest_error_message')
        # The specific error message passed from the sync_report should have been printed
        self.assertTrue(error_message in renderer.prompt.mock_calls[1][1][0])

    def test__display_manifest_sync_report_manifest_in_progress(self):
        """
        Test behavior from _display_manifest_sync_report when the manifest is currently in progress.
        """
        sync_report = progress.SyncProgressReport(None,
                                                  state=progress.SyncProgressReport.
                                                  STATE_MANIFEST_IN_PROGRESS)
        renderer = sp.SyncStatusRenderer(self.context)
        # Let's also put the renderer in the manifest retrieval stage
        renderer._sync_state = progress.SyncProgressReport.STATE_NOT_STARTED
        renderer.prompt.reset_mock()

        renderer._display_manifest_sync_report(sync_report, "goose manifest")

        # There should be one message printed to the user that tells them the
        # manifest is being downloaded
        self.assertEqual(len(renderer.prompt.mock_calls), 1)
        self.assertEqual(renderer.prompt.mock_calls[0][2]['tag'], 'downloading_manifest')
        # The renderer state should have been advanced to
        # STATE_MANIFEST_IN_PROGRESS
        self.assertEqual(renderer._sync_state,
                         progress.SyncProgressReport.STATE_MANIFEST_IN_PROGRESS)

    def test__display_manifest_sync_report_not_started(self):
        """
        Before the download starts, the _display_manifest_sync_report() method
        should not do anything.
        """
        conduit = mock.MagicMock()
        sync_report = progress.SyncProgressReport(conduit,
                                                  state=progress.SyncProgressReport.
                                                  STATE_NOT_STARTED)
        renderer = sp.SyncStatusRenderer(self.context)
        # Let's also put the renderer in the manifest retrieval stage
        renderer._sync_state = progress.SyncProgressReport.STATE_NOT_STARTED
        renderer.prompt.reset_mock()

        renderer._display_manifest_sync_report(sync_report, "swan manifest")

        self.assertEqual(len(renderer.prompt.mock_calls), 0)


class TestHumanReadableBytes(unittest.TestCase):
    """
    Test the human_readable_bytes() method.

    Originally from test_extension_admin_iso_status.py in pulp_rpm
    """

    def setUp(self):
        mock_context = mock.MagicMock()
        mock_prompt = mock.MagicMock()
        mock_context.prompt = mock_prompt
        self.ssr = sp.SyncStatusRenderer(mock_context)

    def test_bytes(self):
        """
        Test correct behavior when bytes are passed in.
        """
        self.assertEqual(self.ssr.human_readable_bytes(42), '42 B')

    def test_kilobytes(self):
        """
        Test correct behavior when kB are passed.
        """
        self.assertEqual(self.ssr.human_readable_bytes(4096), '4.0 kB')

    def test_megabytes(self):
        """
        Test correct behavior when MB are passed.
        """
        self.assertEqual(self.ssr.human_readable_bytes(97464344), '92.9 MB')

    def test_gigabytes(self):
        """
        Test correct behavior when GB are passed.
        """
        self.assertEqual(self.ssr.human_readable_bytes(17584619520), '16.4 GB')

    def test_terabytes(self):
        """
        Test correct behavior when TB are passed.
        """
        self.assertEqual(self.ssr.human_readable_bytes(40444624896000), '36.8 TB')
