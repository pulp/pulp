# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
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
This module tests the pulp.client.commands.repo.upload module.
"""
import datetime
import mock

from pulp.bindings import responses
from pulp.client.commands.repo import upload
from pulp.devel.unit import base


class TestPerformUploadCommand(base.PulpClientTests):
    """
    Test the perform_upload() function.
    """
    @mock.patch('pulp.client.commands.repo.upload.PerformUploadCommand.poll')
    def test_calls_poll(self, poll):
        """
        Make sure that perform_upload() hands off the import task to be polled.
        """
        response_body = {
            'task_id': '123456', 'tags': [], 'start_time': datetime.datetime.now(),
            'finish_time': datetime.datetime.now() + datetime.timedelta(seconds=10),
            'state': responses.STATE_ERROR, 'progress_report': {}, 'result': None,
            'exception': None, 'traceback': None, 'error': 'An error message.', 'spawned_tasks': []}
        response = mock.MagicMock()
        response.response_body = responses.Task(response_body)
        response.is_async = mock.MagicMock(return_value=False)
        upload_manager = mock.MagicMock()
        upload_manager.import_upload = mock.MagicMock(return_value=response)
        upload_ids = ['an_id']
        method = mock.MagicMock()
        user_input = {}
        command = upload.PerformUploadCommand('name', 'description', method, self.context)

        command.perform_upload(self.context, upload_manager, upload_ids, user_input)

        poll.assert_called_once_with([response.response_body], user_input)

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_failure_message')
    def test_import_upload_step_failed(self, render_failure_message):
        """
        Assert that the CLI properly informs the user when an importer reports failure upon
        importing a unit to the repository.
        """
        response_body = {
            'task_id': '123456', 'tags': [], 'start_time': datetime.datetime.now(),
            'finish_time': datetime.datetime.now() + datetime.timedelta(seconds=10),
            'state': responses.STATE_ERROR, 'progress_report': {}, 'result': None,
            'exception': None, 'traceback': None, 'error': 'An error message.', 'spawned_tasks': []}
        response = mock.MagicMock()
        response.response_body = responses.Task(response_body)
        response.is_async = mock.MagicMock(return_value=False)
        upload_manager = mock.MagicMock()
        upload_manager.import_upload = mock.MagicMock(return_value=response)
        upload_ids = ['an_id']
        method = mock.MagicMock()
        user_input = {}
        command = upload.PerformUploadCommand('name', 'description', method, self.context)

        command.perform_upload(self.context, upload_manager, upload_ids, user_input)

        render_failure_message.assert_called_once_with('Task Failed', tag='failed')

    @mock.patch('pulp.client.extensions.core.PulpPrompt.render_failure_message')
    @mock.patch('pulp.client.extensions.core.PulpPrompt.write')
    def test_import_upload_step_succeeded(self, write, render_failure_message):
        """
        Assert that the CLI properly informs the user when an importer reports success upon
        importing a unit to the repository.
        """
        response_body = {
            'task_id': '123456', 'tags': [], 'start_time': datetime.datetime.now(),
            'finish_time': datetime.datetime.now() + datetime.timedelta(seconds=10),
            'state': responses.STATE_FINISHED, 'progress_report': {}, 'result': None,
            'exception': None, 'traceback': None, 'error': None, 'spawned_tasks': []}
        response = mock.MagicMock()
        response.response_body = responses.Task(response_body)
        response.is_async = mock.MagicMock(return_value=False)
        upload_manager = mock.MagicMock()
        upload_manager.import_upload = mock.MagicMock(return_value=response)
        upload_ids = ['an_id']
        method = mock.MagicMock()
        user_input = {}
        command = upload.PerformUploadCommand('name', 'description', method, self.context)

        command.perform_upload(self.context, upload_manager, upload_ids, user_input)

        write.assert_any_call('... completed')
        write.assert_any_call('Task Succeeded', color='\x1b[92m', tag='succeeded')
        # No errors should have been rendered
        self.assertEqual(render_failure_message.call_count, 0)


class UploadCommandTests(base.PulpClientTests):

    def setUp(self):
        super(UploadCommandTests, self).setUp()

        self.mock_upload_manager = mock.MagicMock()
        self.upload_command = upload.UploadCommand(self.context, self.mock_upload_manager)

    def test_verify_repo_exists(self):
        # Setup
        mock_repo_api = mock.MagicMock()
        self.context.server.repo.repository = mock_repo_api

        # Test
        self.upload_command._verify_repo_exists('repo-1')
        # no exception should be raised

    def test_verify_repo_doesnt_exist(self):
        # Setup
        mock_repo_api = mock.MagicMock()
        mock_repo_api.side_effect = Exception()
        self.context.server.repo.repository = mock_repo_api

        # Test
        try:
            self.upload_command._verify_repo_exists('repo-1')
            self.fail('Exception was not bubbled up')
        except Exception, e:
            self.assertTrue(e is mock_repo_api.side_effect)


class ListCommandTests(base.PulpClientTests):

    def test_list_no_filename(self):
        mock_tracker = mock.MagicMock()
        mock_tracker.is_running = False
        mock_tracker.source_filename = None

        self.mock_upload_manager = mock.MagicMock()
        self.mock_upload_manager.list_uploads.return_value = [mock_tracker]
        self.list_command = upload.ListCommand(self.context, self.mock_upload_manager)
        self.list_command.run()
