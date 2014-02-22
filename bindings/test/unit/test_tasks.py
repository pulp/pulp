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
"""
This module contains tests for the pulp.bindings.tasks module.
"""
import unittest

import mock

from pulp.bindings import responses, tasks
from pulp.common import tags


class TaskSearchAPITests(unittest.TestCase):
    """
    Tests for the TaskSearchAPI class.
    """
    def test_PATH(self):
        """
        Make sure the class attribute PATH is correct.
        """
        self.assertEqual(tasks.TaskSearchAPI.PATH, 'v2/tasks/search/')

    @mock.patch('pulp.bindings.search.SearchAPI.search')
    def test_search(self, mock_search):
        """
        Test the search method. All it really does is call the superclass search() method, and turn the
        results into Tasks.
        """
        connection = mock.MagicMock()
        repo_id = 'some_repo'
        repo_tag = tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id)
        sync_tag = tags.action_tag(tags.ACTION_SYNC_TYPE)
        search_criteria = {'filters': {'state': {'$nin': responses.COMPLETED_STATES},
                                       'tags': {'$all': [repo_tag, sync_tag]}}}
        response_body = [{u'task_id': u'3fff3e01-ba48-414c-a4bb-daaed7a0d2d8',
                          u'tags': [u'pulp:repository:%s' % repo_id, u'pulp:action:sync'],
                          u'start_time': 1393098484,
                          u'queue': u'reserved_resource_worker-3@tangerine.rdu.redhat.com',
                          u'state': u'running', u'_id': {u'$oid': u'5308fef46b565fd6740199ae'}}]
        mock_search.return_value = response_body

        results = tasks.TaskSearchAPI(connection).search(**search_criteria)

        mock_search.assert_called_once_with(**search_criteria)
        self.assertEqual(type(results), list)
        self.assertEqual(len(results), 1)
        task = results[0]
        self.assertEqual(type(task), responses.Task)
        self.assertEqual(task.task_id, response_body[0]['task_id'])
        self.assertEqual(task.tags, response_body[0]['tags'])
        self.assertEqual(task.start_time, response_body[0]['start_time'])
        self.assertEqual(task.state, response_body[0]['state'])
