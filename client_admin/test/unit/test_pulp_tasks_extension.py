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

import copy

import base_builtins

from pulp.client.admin import tasks
from pulp.client.extensions.exceptions import NotFoundException, PulpServerException



# -- constants ----------------------------------------------------------------

EXAMPLE_CALL_REPORT = {
    'exception': None,
    'task_type': 'pulp.server.tasks.repository.delete',
    '_href': '/pulp/api/v2/tasks/b2308412-5149-424d-9b04-85a8d6e03067/',
    'task_id': 'c54742d4-9f8b-11e1-9837-00508d977dff',
    'tags': [
        'pulp:repository:f16',
        'pulp:action:sync'
    ],
    'finish_time': '2014-06-05T15:56:12Z',
    '_ns': 'task_status',
    'start_time': None,
    'traceback': None,
    'spawned_tasks': [],
    'progress_report': {},
    'worker_name': 'reserved_resource_worker-3@mhrivnak.rdu.redhat.com',
    'state': 'waiting',
    'result': None,
    'error': None,
    'id': {
        '$oid': '5390931b81a97875924cc0d1'
    }
}

# "pulp-admin tasks list" requests only the fields it needs, and this is an
# example response.
EXAMPLE_LIST_REPORT = {
    '_href': '/pulp/api/v2/tasks/b2308412-5149-424d-9b04-85a8d6e03067/',
    'task_id': 'c54742d4-9f8b-11e1-9837-00508d977dff',
    'tags': [
        'pulp:repository:f16',
        'pulp:action:sync'
    ],
    'finish_time': '2014-06-05T15:56:12Z',
    '_ns': 'task_status',
    'start_time': None,
    'state': 'waiting',
    '_id': {
        '$oid': '5390931b81a97875924cc0d1'
    },
    'id': '5390931b3de3a3290f57e32f'
}


class AllTasksTests(base_builtins.PulpClientTests):

    def setUp(self):
        super(AllTasksTests, self).setUp()

        self.all_tasks_section = tasks.AllTasksSection(self.context, 'tasks', 'desc')

    def test_list_no_tasks(self):
        # Setup
        self.server_mock.request.return_value = (200, [])

        # Test
        self.all_tasks_section.list()

        # Verify correct output
        self.assertTrue('No tasks found\n' in self.recorder.lines)

    def test_list(self):
        # Setup
        self.server_mock.request.return_value = (200, [copy.copy(EXAMPLE_LIST_REPORT)])

        # Test
        self.all_tasks_section.list()

        # Verify - As long as the parsing in the above call didn't fail, this
        # test is happy. Quick check to make sure at least something was displayed
        # to the user.
        self.assertTrue('No tasks found\n' not in self.recorder.lines)
        self.assertTrue('Result:           Incomplete\n' not in self.recorder.lines)

    def test_details(self):
        # Setup
        report = copy.copy(EXAMPLE_CALL_REPORT)
        report['state'] = 'running'
        report['start_time'] = '2012-05-13T19:17:23Z'
        self.server_mock.request.return_value = (200, report)

        # Test
        self.all_tasks_section.details(**{'task-id' : report['task_id']})

        # Verify - As long as the parsing in the above call didn't fail, this
        # test is happy. Quick check to make sure at least something was displayed
        # to the user.
        self.assertTrue(len(self.recorder.lines) > 0)
        self.assertTrue('Result:           Incomplete\n' in self.recorder.lines)

    def test_details_failed_task(self):
        # Setup
        report = copy.copy(EXAMPLE_CALL_REPORT)
        report['state'] = 'error'
        report['start_time'] = '2012-05-13T19:17:23Z'
        report['finish_time'] = '2012-05-13T19:18:23Z'
        report['exception'] = 'Error running operation'
        report['traceback'] = 'Error details'
        self.server_mock.request.return_value = (200, report)

        # Test
        self.all_tasks_section.details(**{'task-id' : report['task_id']})

        # Verify - As long as the parsing in the above call didn't fail, this
        # test is happy. Quick check to make sure at least something was displayed
        # to the user.
        self.assertTrue(len(self.recorder.lines) > 0)

    def test_details_cancelled_task(self):
        # Setup
        report = copy.copy(EXAMPLE_CALL_REPORT)
        report['state'] = 'canceled'
        self.server_mock.request.return_value = (200, report)

        # Test
        self.all_tasks_section.details(**{'task-id' : report['task_id']})

        # Verify - As long as the parsing in the above call didn't fail, this
        # test is happy. Quick check to make sure at least something was displayed
        # to the user.
        self.assertTrue(len(self.recorder.lines) > 0)

    def test_details_finished_task(self):
        # Setup
        report = copy.copy(EXAMPLE_CALL_REPORT)
        report['state'] = 'finished'
        self.server_mock.request.return_value = (200, report)

        # Test
        self.all_tasks_section.details(**{'task-id' : report['task_id']})

        # Verify - As long as the parsing in the above call didn't fail, this
        # test is happy. Quick check to make sure at least something was displayed
        # to the user.
        self.assertTrue(len(self.recorder.lines) > 0)

    def test_details_task_not_found(self):
        # Setup
        self.server_mock.request.return_value = (404, {})

        # Test
        self.assertRaises(NotFoundException, self.all_tasks_section.details, **{'task-id' : 'foo'})

    def test_cancel(self):
        # Setup
        self.server_mock.request.return_value = (200, {})

        # Test
        self.all_tasks_section.cancel(**{'task-id' : 'task_1'})

    def test_cancel_not_found(self):
        # Setup
        self.server_mock.request.return_value = (404, {})

        # Test
        self.assertRaises(NotFoundException, self.all_tasks_section.cancel, **{'task-id' : 'task_1'})

    def test_cancel_not_supported(self):
        """
        An unsupported cancel should be gracefully handled by the CLI instead of
        letting the error propagate up.
        """

        # Setup
        self.server_mock.request.return_value = (501, {'http_status' : 501})

        # Test
        self.all_tasks_section.cancel(**{'task-id' : 'task_1'})

        # Verify
        tags = self.prompt.get_write_tags()
        self.assertTrue('failure' in tags)

    def test_cancel_other_server_error(self):
        """
        All other 500 errors should bubble up.
        """

        # Setup
        self.server_mock.request.return_value = (500, {'http_status' : 500})

        # Test
        self.assertRaises(PulpServerException, self.all_tasks_section.cancel, **{'task-id' : 'task_1'})

class RepoTasksTests(base_builtins.PulpClientTests):

    # Very little needs to be done here other than exercising a call that will
    # call the overridden method

    def setUp(self):
        super(RepoTasksTests, self).setUp()

        self.repo_tasks_section = tasks.RepoTasksSection(self.context, 'tasks', 'desc')

    def test_list(self):
        # Setup
        self.server_mock.request.return_value = (200, [copy.copy(EXAMPLE_CALL_REPORT)])

        # Test
        self.repo_tasks_section.list(**{'repo-id' : 'repo_1'})

        # No errors = success
