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
This module contains tests on the pulp.bindings.responses module.
"""
import unittest

from pulp.bindings import responses


class TestTask(unittest.TestCase):
    """
    This class contains tests on the Task object.
    """
    def test___init__(self):
        """
        Test the __init__() method with some typical data.
        """
        some_typical_data = {
            u'task_id': u'9efb5da2-ff42-4633-9355-81385bd43310',
            u'tags': [u'pulp:repository:zoo', u'pulp:action:sync'], u'finish_time': 1392054742,
            u'_ns': u'task_status', u'start_time': 1392054740,
            u'spawned_tasks': [{u'_href': u'/pulp/api/v2/tasks/37506910-dc71-46c4-809e-48cf385b803f/',
                                u'task_id': u'37506910-dc71-46c4-809e-48cf385b803f'}],
            u'progress_report': {u'some': u'data'},
            u'queue': u'reserved_resource_worker-0@tangerine.rdu.redhat.com', u'state': u'finished',
            u'result': {u'some': u'return data'},
            u'_id': {u'$oid': u'52f911d4b8b0edc2462f61a2'}}

        a_task = responses.Task(some_typical_data)

        # href should default to None when it wasn't in the response data
        self.assertEqual(a_task.href, None)
        self.assertEqual(a_task.task_id, some_typical_data['task_id'])
        self.assertEqual(a_task.tags, some_typical_data['tags'])
        self.assertEqual(a_task.start_time, some_typical_data['start_time'])
        self.assertEqual(a_task.finish_time, some_typical_data['finish_time'])
        self.assertEqual(a_task.state, some_typical_data['state'])
        self.assertEqual(a_task.progress_report, some_typical_data['progress_report'])
        self.assertEqual(a_task.result, some_typical_data['result'])
        # exception, traceback and error default to None when it isn't provided in the response data
        self.assertEqual(a_task.exception, None)
        self.assertEqual(a_task.traceback, None)
        self.assertEqual(a_task.error, None)
        # Spawned tasks end up being Task objects, so we'll need to inspect more manually
        self.assertEqual(len(a_task.spawned_tasks), 1)
        self.assertEqual(type(a_task.spawned_tasks), list)
        self.assertEqual(type(a_task.spawned_tasks[0]), responses.Task)
        self.assertEqual(a_task.spawned_tasks[0].href, some_typical_data['spawned_tasks'][0]['_href'])
        self.assertEqual(a_task.spawned_tasks[0].task_id, some_typical_data['spawned_tasks'][0]['task_id'])

    def test___init___with_exception(self):
        """
        Test __init__() when there is an exception.
        """
        some_typical_data = {
            u'task_id': u'9efb5da2-ff42-4633-9355-81385bd43310',
            u'exception': u'TheWorldIsEndingException',
            u'traceback': u'deprecated traceback here',
            u'error': u'Some error message',
            u'tags': [u'pulp:repository:zoo', u'pulp:action:sync'], u'finish_time': 1392054742,
            u'_ns': u'task_status', u'start_time': 1392054740,
            u'progress_report': {u'some': u'data'},
            u'queue': u'reserved_resource_worker-0@tangerine.rdu.redhat.com', u'state': responses.STATE_ERROR,
            u'_id': {u'$oid': u'52f911d4b8b0edc2462f61a2'}}

        a_task = responses.Task(some_typical_data)

        # href should default to None when it wasn't in the response data
        self.assertEqual(a_task.href, None)
        self.assertEqual(a_task.task_id, some_typical_data['task_id'])
        self.assertEqual(a_task.tags, some_typical_data['tags'])
        self.assertEqual(a_task.start_time, some_typical_data['start_time'])
        self.assertEqual(a_task.finish_time, some_typical_data['finish_time'])
        self.assertEqual(a_task.state, some_typical_data['state'])
        self.assertEqual(a_task.progress_report, some_typical_data['progress_report'])
        self.assertEqual(a_task.result, None)
        # exception, traceback and error default to None when it isn't provided in the response data
        self.assertEqual(a_task.exception, some_typical_data['exception'])
        self.assertEqual(a_task.traceback, some_typical_data['traceback'])
        self.assertEqual(a_task.error, some_typical_data['error'])
        # Spawned tasks defaults to [] if None are in the response_body
        self.assertEqual(a_task.spawned_tasks, [])

    def test___init___with_href(self):
        """
        There isn't always an _href in the response data. Assert that we handle it when it is present.
        """
        some_typical_data = {
            u'_href': u'/pulp/api/v2/tasks/9efb5da2-ff42-4633-9355-81385bd43310',
            u'task_id': u'9efb5da2-ff42-4633-9355-81385bd43310',
            u'tags': [u'pulp:repository:zoo', u'pulp:action:sync'], u'finish_time': 1392054742,
            u'_ns': u'task_status', u'start_time': 1392054740,
            u'spawned_tasks': [{u'_href': u'/pulp/api/v2/tasks/37506910-dc71-46c4-809e-48cf385b803f/',
                                u'task_id': u'37506910-dc71-46c4-809e-48cf385b803f'}],
            u'progress_report': {u'some': u'data'},
            u'queue': u'reserved_resource_worker-0@tangerine.rdu.redhat.com', u'state': u'finished',
            u'result': {u'some': u'return data'},
            u'_id': {u'$oid': u'52f911d4b8b0edc2462f61a2'}}

        a_task = responses.Task(some_typical_data)

        self.assertEqual(a_task.href, some_typical_data['_href'])
        self.assertEqual(a_task.task_id, some_typical_data['task_id'])
        self.assertEqual(a_task.tags, some_typical_data['tags'])
        self.assertEqual(a_task.start_time, some_typical_data['start_time'])
        self.assertEqual(a_task.finish_time, some_typical_data['finish_time'])
        self.assertEqual(a_task.state, some_typical_data['state'])
        self.assertEqual(a_task.progress_report, some_typical_data['progress_report'])
        self.assertEqual(a_task.result, some_typical_data['result'])
        # exception, traceback and error default to None when it isn't provided in the response data
        self.assertEqual(a_task.exception, None)
        self.assertEqual(a_task.traceback, None)
        self.assertEqual(a_task.error, None)
        # Spawned tasks end up being Task objects, so we'll need to inspect more manually
        self.assertEqual(len(a_task.spawned_tasks), 1)
        self.assertEqual(type(a_task.spawned_tasks), list)
        self.assertEqual(type(a_task.spawned_tasks[0]), responses.Task)
        self.assertEqual(a_task.spawned_tasks[0].href, some_typical_data['spawned_tasks'][0]['_href'])
        self.assertEqual(a_task.spawned_tasks[0].task_id, some_typical_data['spawned_tasks'][0]['task_id'])

    def test___str__(self):
        """
        Test the __str__() method.
        """
        some_typical_data = {
            u'_href': u'/pulp/api/v2/tasks/9efb5da2-ff42-4633-9355-81385bd43310',
            u'task_id': u'9efb5da2-ff42-4633-9355-81385bd43310',
            u'tags': [u'pulp:repository:zoo', u'pulp:action:sync'], u'finish_time': 1392054742,
            u'_ns': u'task_status', u'start_time': 1392054740,
            u'spawned_tasks': [{u'_href': u'/pulp/api/v2/tasks/37506910-dc71-46c4-809e-48cf385b803f/',
                                u'task_id': u'37506910-dc71-46c4-809e-48cf385b803f'}],
            u'progress_report': {u'some': u'data'},
            u'queue': u'reserved_resource_worker-0@tangerine.rdu.redhat.com', u'state': u'finished',
            u'result': {u'some': u'return data'},
            u'_id': {u'$oid': u'52f911d4b8b0edc2462f61a2'}}
        a_task = responses.Task(some_typical_data)

        representation = str(a_task)

        expected_representation = u'Task: 9efb5da2-ff42-4633-9355-81385bd43310 State: finished'
        self.assertEqual(representation, expected_representation)
