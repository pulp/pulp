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

import datetime
import traceback
import unittest

import mock

import base

from pulp.server.compat import ObjectId
from pulp.server.db.model.dispatch import CallResource, QueuedCall, ArchivedCall
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import call
from pulp.server.dispatch import coordinator
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.dispatch.task import Task
from pulp.server.exceptions import OperationTimedOut
from pulp.server.util import CycleExists, topological_sort

# coordinator instantiation tests ----------------------------------------------

class CoordinatorInstantiationTests(base.PulpServerTests):

    def test_instantiation(self):
        try:
            coordinator.Coordinator()
        except:
            self.fail(traceback.format_exc())

# coordinator base tests -------------------------------------------------------

class CoordinatorTests(base.PulpServerTests):

    def setUp(self):
        super(CoordinatorTests, self).setUp()
        self.coordinator = coordinator.Coordinator()
        self._task_queue_factory = dispatch_factory._task_queue
        dispatch_factory._task_queue = mock.Mock() # replace the task queue
        self.collection = CallResource.get_collection()

    def tearDown(self):
        super(CoordinatorTests, self).tearDown()
        self.coordinator = None
        dispatch_factory._task_queue = self._task_queue_factory
        self._task_queue_factory = None
        self.collection.drop()
        self.collection = None
        QueuedCall.get_collection().drop()
        ArchivedCall.get_collection().drop()

# or query tests ---------------------------------------------------------------

class OrQueryTests(CoordinatorTests):

    def test_task_records_insertion(self):
        task_id = 'my_task'
        repo_id = 'my_repo'
        content_unit_id = 'my_content_unit'
        resources = {
            dispatch_constants.RESOURCE_REPOSITORY_TYPE: {
                repo_id: dispatch_constants.RESOURCE_UPDATE_OPERATION,
            },
            dispatch_constants.RESOURCE_CONTENT_UNIT_TYPE: {
                content_unit_id: [dispatch_constants.RESOURCE_READ_OPERATION],
            }
        }
        try:
            call_resources = coordinator.resource_dict_to_call_resources(resources)
            coordinator.set_call_request_id_on_call_resources(task_id, call_resources)
            self.collection.insert(call_resources, safe=True)
        except:
            self.fail(traceback.format_exc())

    def test_single_resource_or_query(self):
        repo_id = 'my_repo'
        resources = {
            dispatch_constants.RESOURCE_REPOSITORY_TYPE: {
                repo_id: dispatch_constants.RESOURCE_READ_OPERATION
            }
        }
        call_resources = coordinator.resource_dict_to_call_resources(resources)
        self.collection.insert(call_resources, safe=True)

        or_query = {'$or': coordinator.filter_dicts(call_resources, ('resource_type', 'resource_id'))}
        cursor = self.collection.find(or_query)
        self.assertTrue(cursor.count() == 1, '%d' % cursor.count())

    def test_multiple_resources_or_query_single_result(self):
        repo_1_id = 'original'
        repo_2_id = 'clone'
        resources = {
            dispatch_constants.RESOURCE_REPOSITORY_TYPE: {
                repo_1_id: dispatch_constants.RESOURCE_READ_OPERATION,
                repo_2_id: dispatch_constants.RESOURCE_CREATE_OPERATION,
            }
        }
        call_resources = coordinator.resource_dict_to_call_resources(resources)
        self.collection.insert(call_resources, safe=True)

        or_query = {'$or': [{'resource_type': dispatch_constants.RESOURCE_REPOSITORY_TYPE, 'resource_id': repo_2_id}]}
        cursor = self.collection.find(or_query)
        self.assertTrue(cursor.count() == 1, '%d' % cursor.count())

    def test_multiple_resources_or_query_multiple_results(self):
        repo_1_id = 'original'
        repo_2_id = 'clone'
        resources = {
            dispatch_constants.RESOURCE_REPOSITORY_TYPE: {
                repo_1_id: dispatch_constants.RESOURCE_READ_OPERATION,
                repo_2_id: dispatch_constants.RESOURCE_CREATE_OPERATION,
                }
        }
        call_resources = coordinator.resource_dict_to_call_resources(resources)
        self.collection.insert(call_resources, safe=True)

        or_query = coordinator.filter_dicts(call_resources, ('resource_type', 'resource_id'))
        cursor = self.collection.find({'$or': or_query})
        self.assertTrue(cursor.count() == 2, '%d' % cursor.count())

# conflicting operations tests -------------------------------------------------

class ConflictingOperationsTests(base.PulpServerTests):

    def test_postponing_operations_for_create(self):
        postponing_operations = coordinator.get_postponing_operations(dispatch_constants.RESOURCE_CREATE_OPERATION)
        self.assertFalse(dispatch_constants.RESOURCE_CREATE_OPERATION in postponing_operations)
        self.assertTrue(dispatch_constants.RESOURCE_READ_OPERATION in postponing_operations)
        self.assertTrue(dispatch_constants.RESOURCE_UPDATE_OPERATION in postponing_operations)
        self.assertTrue(dispatch_constants.RESOURCE_DELETE_OPERATION in postponing_operations)

    def test_postponing_operations_for_read(self):
        postponing_operations = coordinator.get_postponing_operations(dispatch_constants.RESOURCE_READ_OPERATION)
        self.assertTrue(dispatch_constants.RESOURCE_CREATE_OPERATION in postponing_operations)
        self.assertFalse(dispatch_constants.RESOURCE_READ_OPERATION in postponing_operations)
        self.assertFalse(dispatch_constants.RESOURCE_UPDATE_OPERATION in postponing_operations)
        self.assertFalse(dispatch_constants.RESOURCE_DELETE_OPERATION in postponing_operations)

    def test_postponing_operations_for_update(self):
        postponing_operations = coordinator.get_postponing_operations(dispatch_constants.RESOURCE_UPDATE_OPERATION)
        self.assertTrue(dispatch_constants.RESOURCE_CREATE_OPERATION in postponing_operations)
        self.assertTrue(dispatch_constants.RESOURCE_READ_OPERATION in postponing_operations)
        self.assertTrue(dispatch_constants.RESOURCE_UPDATE_OPERATION in postponing_operations)
        self.assertFalse(dispatch_constants.RESOURCE_DELETE_OPERATION in postponing_operations)

    def test_postponing_operations_for_delete(self):
        postponing_operations = coordinator.get_postponing_operations(dispatch_constants.RESOURCE_DELETE_OPERATION)
        self.assertTrue(dispatch_constants.RESOURCE_CREATE_OPERATION in postponing_operations)
        self.assertTrue(dispatch_constants.RESOURCE_READ_OPERATION in postponing_operations)
        self.assertTrue(dispatch_constants.RESOURCE_UPDATE_OPERATION in postponing_operations)
        self.assertFalse(dispatch_constants.RESOURCE_DELETE_OPERATION in postponing_operations)

    def test_rejecting_operations_for_create(self):
        rejecting_operations = coordinator.get_rejecting_operations(dispatch_constants.RESOURCE_CREATE_OPERATION)
        self.assertTrue(dispatch_constants.RESOURCE_CREATE_OPERATION in rejecting_operations)
        self.assertFalse(dispatch_constants.RESOURCE_READ_OPERATION in rejecting_operations)
        self.assertFalse(dispatch_constants.RESOURCE_UPDATE_OPERATION in rejecting_operations)
        self.assertFalse(dispatch_constants.RESOURCE_DELETE_OPERATION in rejecting_operations)

    def test_rejecting_operations_for_read(self):
        rejecting_operations = coordinator.get_rejecting_operations(dispatch_constants.RESOURCE_READ_OPERATION)
        self.assertFalse(dispatch_constants.RESOURCE_CREATE_OPERATION in rejecting_operations)
        self.assertFalse(dispatch_constants.RESOURCE_READ_OPERATION in rejecting_operations)
        self.assertFalse(dispatch_constants.RESOURCE_UPDATE_OPERATION in rejecting_operations)
        self.assertTrue(dispatch_constants.RESOURCE_DELETE_OPERATION in rejecting_operations)

    def test_rejecting_operations_for_update(self):
        rejecting_operations = coordinator.get_rejecting_operations(dispatch_constants.RESOURCE_UPDATE_OPERATION)
        self.assertFalse(dispatch_constants.RESOURCE_CREATE_OPERATION in rejecting_operations)
        self.assertFalse(dispatch_constants.RESOURCE_READ_OPERATION in rejecting_operations)
        self.assertFalse(dispatch_constants.RESOURCE_UPDATE_OPERATION in rejecting_operations)
        self.assertTrue(dispatch_constants.RESOURCE_DELETE_OPERATION in rejecting_operations)

    def test_rejecting_operations_for_delete(self):
        rejecting_operations = coordinator.get_rejecting_operations(dispatch_constants.RESOURCE_DELETE_OPERATION)
        self.assertFalse(dispatch_constants.RESOURCE_CREATE_OPERATION in rejecting_operations)
        self.assertFalse(dispatch_constants.RESOURCE_READ_OPERATION in rejecting_operations)
        self.assertFalse(dispatch_constants.RESOURCE_UPDATE_OPERATION in rejecting_operations)
        self.assertTrue(dispatch_constants.RESOURCE_DELETE_OPERATION in rejecting_operations)

# collision detection tests ----------------------------------------------------

class CoordinatorCollisionDetectionTests(CoordinatorTests):

    def test_no_conflicts(self):
        task_id = 'existing_task'
        cds_id = 'my_cds'
        resources = {
            dispatch_constants.RESOURCE_CDS_TYPE: {
                cds_id: dispatch_constants.RESOURCE_READ_OPERATION
            }
        }

        # read does not conflict with read

        call_resources = coordinator.resource_dict_to_call_resources(resources)
        coordinator.set_call_request_id_on_call_resources(task_id, call_resources)
        self.collection.insert(call_resources, safe=True)

        response, blockers, reasons, call_resources = self.coordinator._find_conflicts(resources)

        self.assertTrue(response is dispatch_constants.CALL_ACCEPTED_RESPONSE)
        self.assertFalse(blockers)
        self.assertFalse(reasons)

    def test_single_conflict(self):
        # modeling adding a content unit to a repository
        task_id = 'existing_task'
        repo_id = 'my_repo'
        content_unit_id = 'my_content_unit'
        existing_resources = {
            dispatch_constants.RESOURCE_REPOSITORY_TYPE: {
                repo_id: dispatch_constants.RESOURCE_UPDATE_OPERATION
            },
            dispatch_constants.RESOURCE_CONTENT_UNIT_TYPE: {
                content_unit_id: dispatch_constants.RESOURCE_READ_OPERATION
            }
        }
        existing_task_resources = coordinator.resource_dict_to_call_resources(existing_resources)
        coordinator.set_call_request_id_on_call_resources(task_id, existing_task_resources)
        self.collection.insert(existing_task_resources, safe=True)

        # delete on content unit is postponed by read

        resources = {
            dispatch_constants.RESOURCE_CONTENT_UNIT_TYPE: {
                content_unit_id: dispatch_constants.RESOURCE_DELETE_OPERATION
            }
        }
        response, blockers, reasons, call_resources = self.coordinator._find_conflicts(resources)

        self.assertTrue(response is dispatch_constants.CALL_POSTPONED_RESPONSE)
        self.assertTrue(task_id in blockers)
        self.assertTrue(reasons)


    def test_multiple_conflicts(self):
        # modeling binding a consumer group to a repository
        call_1_id = 'first_task'
        call_2_id = 'second_task'
        repo_id = 'my_awesome_repo'
        consumer_1_id = 'my_awesome_consumer'
        consumer_2_id = 'my_less_awesome_consumer'

        bind_1_resources = {
            dispatch_constants.RESOURCE_REPOSITORY_TYPE: {
                repo_id: dispatch_constants.RESOURCE_READ_OPERATION
            },
            dispatch_constants.RESOURCE_CONSUMER_TYPE: {
                consumer_1_id: dispatch_constants.RESOURCE_UPDATE_OPERATION
            }
        }
        bind_2_resources = {
            dispatch_constants.RESOURCE_REPOSITORY_TYPE: {
                repo_id: dispatch_constants.RESOURCE_READ_OPERATION
            },
            dispatch_constants.RESOURCE_CONSUMER_TYPE: {
                consumer_2_id: [dispatch_constants.RESOURCE_UPDATE_OPERATION]
            }
        }

        task_1_resources = coordinator.resource_dict_to_call_resources(bind_1_resources)
        coordinator.set_call_request_id_on_call_resources(call_1_id, task_1_resources)

        task_2_resources = coordinator.resource_dict_to_call_resources(bind_2_resources)
        coordinator.set_call_request_id_on_call_resources(call_2_id, task_2_resources)

        self.collection.insert(task_1_resources, safe=True)
        self.collection.insert(task_2_resources, safe=True)

        # deleting the repository should be postponed by both binds

        resources = {
            dispatch_constants.RESOURCE_REPOSITORY_TYPE: {
                repo_id: dispatch_constants.RESOURCE_DELETE_OPERATION
            }
        }

        response, blockers, reasons, call_resources = self.coordinator._find_conflicts(resources)

        self.assertTrue(response is dispatch_constants.CALL_POSTPONED_RESPONSE, response)
        self.assertTrue(call_1_id in blockers)
        self.assertTrue(call_2_id in blockers)
        self.assertTrue(reasons)

    def test_rejected(self):
        # modeling a cds deletion
        task_id = 'cds_deletion'
        cds_id = 'less_than_awesome_cds'
        deletion_resources = {
            dispatch_constants.RESOURCE_CDS_TYPE: {
                cds_id: dispatch_constants.RESOURCE_DELETE_OPERATION
            }
        }
        deletion_task_resources = coordinator.resource_dict_to_call_resources(deletion_resources)
        coordinator.set_call_request_id_on_call_resources(task_id, deletion_task_resources)
        self.collection.insert(deletion_task_resources, safe=True)

        # a cds sync should be rejected by the deletion

        resources = {
            dispatch_constants.RESOURCE_CDS_TYPE: {
                cds_id: dispatch_constants.RESOURCE_UPDATE_OPERATION
            },
            dispatch_constants.RESOURCE_REPOSITORY_TYPE: {
                'some_repo': dispatch_constants.RESOURCE_READ_OPERATION
            }
        }

        response, blockers, reasons, call_resources = self.coordinator._find_conflicts(resources)

        self.assertTrue(response is dispatch_constants.CALL_REJECTED_RESPONSE)
        self.assertTrue(task_id in blockers)
        self.assertTrue(reasons)

# call execution tests ---------------------------------------------------------

def dummy_call(progress, success, failure):
    pass


class CoordinatorRunTaskTests(CoordinatorTests):

    def setUp(self):
        super(CoordinatorRunTaskTests, self).setUp()
        self._wait_for_task = coordinator.wait_for_task
        coordinator.wait_for_task = mock.Mock()

    def tearDown(self):
        super(CoordinatorRunTaskTests, self).tearDown()
        coordinator.wait_for_task = self._wait_for_task

    def test_run_task_async(self):
        task = Task(call.CallRequest(dummy_call))
        self.coordinator._process_tasks([task])
        self.assertTrue(len(task.call_request.execution_hooks[dispatch_constants.CALL_ENQUEUE_LIFE_CYCLE_CALLBACK]) == 1)
        self.assertTrue(len(task.call_request.execution_hooks[dispatch_constants.CALL_DEQUEUE_LIFE_CYCLE_CALLBACK]) == 2)
        self.assertTrue(coordinator.coordinator_dequeue_callback in task.call_request.execution_hooks[dispatch_constants.CALL_DEQUEUE_LIFE_CYCLE_CALLBACK])

    def test_run_task_sync(self):
        task = Task(call.CallRequest(dummy_call))
        self.coordinator._process_tasks([task])
        self.coordinator._run_task(task)
        self.assertTrue(coordinator.wait_for_task.call_count == 2, coordinator.wait_for_task.call_count)


class CoordinatorWaitForTaskTests(CoordinatorTests):

    def test_run_task_sync_timeout(self):
        task = Task(call.CallRequest(dummy_call))
        timeout = datetime.timedelta(seconds=0.001)
        self.assertRaises(OperationTimedOut,
                          self.coordinator._run_task,
                          task, timeout)


class CoordinatorCallExecutionTests(CoordinatorTests):

    def setUp(self):
        super(CoordinatorCallExecutionTests, self).setUp()
        self.coordinator._process_tasks = mock.Mock()
        self.coordinator._run_task = mock.Mock()

    def test_execute_call(self):
        call_request = call.CallRequest(dummy_call)
        call_report = self.coordinator.execute_call(call_request)
        self.assertTrue(isinstance(call_report, call.CallReport))
        self.assertTrue(self.coordinator._process_tasks.call_count == 1)
        task = self.coordinator._process_tasks.call_args[0][0][0]
        self.assertTrue(isinstance(task, Task))
        self.assertTrue(call_report.call_request_id == task.call_request.id, '"%s" != "%s"' % (call_report.call_request_id, task.call_request.id))

    def test_execute_call_synchronously(self):
        call_request = call.CallRequest(dummy_call)
        self.coordinator.execute_call_synchronously(call_request)
        self.assertTrue(self.coordinator._process_tasks.call_count == 1)
        self.assertTrue(self.coordinator._run_task.call_count == 1)

    def test_execute_call_asynchronously(self):
        call_request = call.CallRequest(dummy_call)
        self.coordinator.execute_call_asynchronously(call_request)
        self.assertTrue(self.coordinator._process_tasks.call_count == 1)
        self.assertTrue(self.coordinator._run_task.call_count == 0)

# multiple call execution tests ------------------------------------------------

class TopologicalSortTests(unittest.TestCase):

    def test_disconnected_graph(self):
        v1 = 'vertex 1'
        v2 = 'vertex 2'
        v3 = 'vertex 3'
        graph = {v1: [],
                 v2: [],
                 v3: []}
        sorted_vertices = topological_sort(graph)
        for v in (v1, v2, v3):
            self.assertTrue(v in sorted_vertices, v)
        self.assertTrue(len(sorted_vertices) == len(graph))

    def test_acyclic_graph(self):
        v1 = 'vertex 1'
        v2 = 'vertex 2'
        v3 = 'vertex 3'
        graph = {v1: [v2, v3],
                 v2: [v3],
                 v3: []}
        sorted_vertices = topological_sort(graph)
        self.assertTrue(len(sorted_vertices) == len(graph))
        self.assertTrue(v3 is sorted_vertices[0])

    def test_cyclic_graph(self):
        v1 = 'vertex 1'
        v2 = 'vertex 2'
        v3 = 'vertex 3'
        graph = {v1: [v2, v3],
                 v2: [v3],
                 v3: [v1]}
        self.assertRaises(CycleExists,
                          topological_sort,
                          graph)

    def test_single_vertex_cyclic_graph(self):
        v1 = 'vertex 1'
        graph = {v1: [v1]}
        self.assertRaises(CycleExists,
                          topological_sort,
                          graph)


class CoordinatorMultipleCallExecutionTests(CoordinatorTests):

    def setUp(self):
        super(CoordinatorMultipleCallExecutionTests, self).setUp()
        self.mock(self.coordinator, '_process_tasks')

    def test_execute_multiple_calls(self):
        call_requests = [call.CallRequest(dummy_call), call.CallRequest(dummy_call)]
        call_reports = self.coordinator.execute_multiple_calls(call_requests)
        self.assertTrue(len(call_requests) == len(call_reports))
        self.assertTrue(self.coordinator._process_tasks.call_count == 1)

    def test_execute_multiple_calls_dependencies(self):
        call_request_1 = call.CallRequest(dummy_call)
        call_request_2 = call.CallRequest(dummy_call)
        call_request_3 = call.CallRequest(dummy_call)

        # use the convenience api
        call_request_3.depends_on(call_request_1.id)
        call_request_3.depends_on(call_request_2.id)
        call_request_2.depends_on(call_request_1.id)

        call_requests = [call_request_3, call_request_2, call_request_1]

        call_reports = self.coordinator.execute_multiple_calls(call_requests)
        self.assertTrue(len(call_requests) == len(call_reports))
        self.assertTrue(self.coordinator._process_tasks.call_count == 1)

    def test_execute_multiple_calls_circular_dependencies(self):
        call_request_1 = call.CallRequest(dummy_call)
        call_request_2 = call.CallRequest(dummy_call)
        call_request_3 = call.CallRequest(dummy_call)

        call_request_1.dependencies = {call_request_3.id: None}
        call_request_2.dependencies = {call_request_1.id: None}
        call_request_3.dependencies = {call_request_1.id: None,
                                       call_request_2.id: None}

        call_requests = [call_request_3, call_request_2, call_request_1]

        self.assertRaises(CycleExists,
                          self.coordinator.execute_multiple_calls,
                          call_requests)
        self.assertTrue(self.coordinator._process_tasks.call_count == 0)

    def test_task_blockers_from_dependencies(self):
        call_request_1 = call.CallRequest(dummy_call)
        call_request_2 = call.CallRequest(dummy_call)

        call_request_2.depends_on(call_request_1.id)

        self.coordinator.execute_multiple_calls([call_request_2, call_request_1])

        task_1 = self.coordinator._process_tasks.call_args_list[0][0][0][0]
        task_2 = self.coordinator._process_tasks.call_args_list[0][0][0][1]

        self.assertTrue(task_1.call_request is call_request_1)
        self.assertTrue(task_2.call_request is call_request_2)
        self.assertTrue(task_1.call_request.id in task_2.call_request.dependencies)
        self.assertFalse(task_2.call_request.id in task_1.call_request.dependencies)


class CoordinatorMultipleCallRejectedTests(CoordinatorTests):

    def setUp(self):
        super(CoordinatorMultipleCallRejectedTests, self).setUp()
        self.coordinator._find_conflicts = mock.Mock(return_value=(dispatch_constants.CALL_REJECTED_RESPONSE, set(), [], []))

    def test_execute_multiple_rejected(self):
        call_request_1 = call.CallRequest(dummy_call)
        call_request_2 = call.CallRequest(dummy_call)

        call_report_list = self.coordinator.execute_multiple_calls([call_request_1, call_request_2])

        self.assertEqual(self.coordinator._find_conflicts.call_count, 2)

        self.assertEqual(call_report_list[0].response, dispatch_constants.CALL_REJECTED_RESPONSE)
        self.assertEqual(call_report_list[1].response, dispatch_constants.CALL_REJECTED_RESPONSE)

# coordinator find tests -------------------------------------------------------

def find_dummy_call(*args, **kwargs):
    pass


class CoordinatorFindCallReportsTests(CoordinatorTests):

    def set_task_queue(self, task_list):
        mocked_task_queue = mock.Mock()
        mocked_task_queue.all_tasks = mock.Mock(return_value=task_list)
        # this gets cleaned up by the base class tearDown method
        dispatch_factory._task_queue = mock.Mock(return_value=mocked_task_queue)

    def test_find_by_schedule_id(self):
        schedule_id = str(ObjectId())
        call_request = call.CallRequest(find_dummy_call)
        call_report = call.CallReport.from_call_request(call_request)
        call_report.schedule_id = schedule_id
        task = Task(call_request, call_report)
        self.set_task_queue([task])

        call_report_list = self.coordinator.find_call_reports(schedule_id=schedule_id)
        self.assertEqual(len(call_report_list), 1)
        self.assertEqual(call_report_list[0].schedule_id, schedule_id)

    def test_find_by_call_request_id_list(self):
        call_request = call.CallRequest(find_dummy_call)
        task = Task(call_request)
        self.set_task_queue([task])

        call_report_list = self.coordinator.find_call_reports(call_request_id_list=[call_request.id])
        self.assertEqual(len(call_report_list), 1)
        self.assertEqual(call_report_list[0].call_request_id, call_request.id)

# coordinator start tests ------------------------------------------------------

class CoordinatorStartTests(CoordinatorTests):

    def setUp(self):
        super(CoordinatorStartTests, self).setUp()
        self.queued_call_collection = QueuedCall.get_collection()
        self.coordinator.execute_call_asynchronously = mock.Mock()
        self.coordinator.execute_multiple_calls = mock.Mock()

    def tearDown(self):
        super(CoordinatorStartTests, self).tearDown()

    def test_start_bad_queued_call_none(self):
        self.queued_call_collection.insert({'serialized_call_request': None})

        self.coordinator.start()

        self.assertEqual(self.coordinator.execute_call_asynchronously.call_count, 0)
        self.assertEqual(self.coordinator.execute_multiple_calls.call_count, 0)

    def test_start_bad_queued_call_missing_fields(self):
        self.queued_call_collection.insert({'serialized_call_request': {}})

        self.coordinator.start()

        self.assertEqual(self.coordinator.execute_call_asynchronously.call_count, 0)
        self.assertEqual(self.coordinator.execute_multiple_calls.call_count, 0)

    def test_start_good_queued_call(self):
        request = call.CallRequest(dummy_call)
        queued_request = QueuedCall(request)
        self.queued_call_collection.insert(queued_request)

        self.coordinator.start()

        self.assertEqual(self.coordinator.execute_call_asynchronously.call_count, 1)
        self.assertEqual(self.coordinator.execute_multiple_calls.call_count, 0)

    def test_start_good_queued_call_collection(self):
        request_1 = call.CallRequest(dummy_call)
        request_2 = call.CallRequest(dummy_call)
        request_1.group_id = request_2.group_id = 'my-group'

        queued_request_1 = QueuedCall(request_1)
        queued_request_2 = QueuedCall(request_2)
        self.queued_call_collection.insert(queued_request_1)
        self.queued_call_collection.insert(queued_request_2)

        self.coordinator.start()

        self.assertEqual(self.coordinator.execute_call_asynchronously.call_count, 0)
        self.assertEqual(self.coordinator.execute_multiple_calls.call_count, 1)


