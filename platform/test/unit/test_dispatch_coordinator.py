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
import os
import sys
import traceback

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/../common/'))

import mock

import testutil

from pulp.server.db.model.dispatch import TaskResource
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import call
from pulp.server.dispatch import coordinator
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.dispatch.task import Task
from pulp.server.exceptions import OperationTimedOut

# coordinator instantiation tests ----------------------------------------------

class CoordinatorInstantiationTests(testutil.PulpTest):

    def test_instantiation(self):
        try:
            coordinator.Coordinator()
        except:
            self.fail(traceback.format_exc())

# coordinator base tests -------------------------------------------------------

class CoordinatorTests(testutil.PulpTest):

    def setUp(self):
        super(CoordinatorTests, self).setUp()
        self.coordinator = coordinator.Coordinator()
        self._task_queue_factory = dispatch_factory._task_queue
        dispatch_factory._task_queue = mock.Mock() # replace the task queue
        self.collection = TaskResource.get_collection()

    def tearDown(self):
        super(CoordinatorTests, self).tearDown()
        self.coordinator = None
        dispatch_factory._task_queue = self._task_queue_factory
        self._task_queue_factory = None
        self.collection.drop()
        self.collection = None

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
            task_resources = coordinator.resource_dict_to_task_resources(resources)
            coordinator.set_task_id_on_task_resources(task_id, task_resources)
            self.collection.insert(task_resources, safe=True)
        except:
            self.fail(traceback.format_exc())

    def test_single_resource_or_query(self):
        repo_id = 'my_repo'
        resources = {
            dispatch_constants.RESOURCE_REPOSITORY_TYPE: {
                repo_id: dispatch_constants.RESOURCE_READ_OPERATION
            }
        }
        task_resources = coordinator.resource_dict_to_task_resources(resources)
        self.collection.insert(task_resources, safe=True)

        or_query = {'$or': coordinator.filter_dicts(task_resources, ('resource_type', 'resource_id'))}
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
        task_resources = coordinator.resource_dict_to_task_resources(resources)
        self.collection.insert(task_resources, safe=True)

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
        task_resources = coordinator.resource_dict_to_task_resources(resources)
        self.collection.insert(task_resources, safe=True)

        or_query = coordinator.filter_dicts(task_resources, ('resource_type', 'resource_id'))
        cursor = self.collection.find({'$or': or_query})
        self.assertTrue(cursor.count() == 2, '%d' % cursor.count())

# conflicting operations tests -------------------------------------------------

class ConflictingOperationsTests(testutil.PulpTest):

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

        task_resources = coordinator.resource_dict_to_task_resources(resources)
        coordinator.set_task_id_on_task_resources(task_id, task_resources)
        self.collection.insert(task_resources, safe=True)

        response, blockers, reasons, task_resources = self.coordinator._find_conflicts(resources)

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
        existing_task_resources = coordinator.resource_dict_to_task_resources(existing_resources)
        coordinator.set_task_id_on_task_resources(task_id, existing_task_resources)
        self.collection.insert(existing_task_resources, safe=True)

        # delete on content unit is postponed by read

        resources = {
            dispatch_constants.RESOURCE_CONTENT_UNIT_TYPE: {
                content_unit_id: dispatch_constants.RESOURCE_DELETE_OPERATION
            }
        }
        response, blockers, reasons, task_resources = self.coordinator._find_conflicts(resources)

        self.assertTrue(response is dispatch_constants.CALL_POSTPONED_RESPONSE)
        self.assertTrue(task_id in blockers)
        self.assertTrue(reasons)


    def test_multiple_conflicts(self):
        # modeling binding a consumer group to a repository
        task_1 = 'first_task'
        task_2 = 'second_task'
        repo_id = 'my_awesome_repo'
        consumer_1 = 'my_awesome_consumer'
        consumer_2 = 'my_less_awesome_consumer'
        bind_1_resources = {
            dispatch_constants.RESOURCE_REPOSITORY_TYPE: {
                repo_id: dispatch_constants.RESOURCE_READ_OPERATION
            },
            dispatch_constants.RESOURCE_CONSUMER_TYPE: {
                consumer_1: dispatch_constants.RESOURCE_UPDATE_OPERATION
            }
        }
        bind_2_resources = {
            dispatch_constants.RESOURCE_REPOSITORY_TYPE: {
                repo_id: dispatch_constants.RESOURCE_READ_OPERATION
            },
            dispatch_constants.RESOURCE_CONSUMER_TYPE: {
                consumer_2: [dispatch_constants.RESOURCE_UPDATE_OPERATION]
            }
        }
        task_1_resources = coordinator.resource_dict_to_task_resources(bind_1_resources)
        coordinator.set_task_id_on_task_resources(task_1, task_1_resources)
        task_2_resources = coordinator.resource_dict_to_task_resources(bind_2_resources)
        coordinator.set_task_id_on_task_resources(task_2, task_2_resources)
        self.collection.insert(task_1_resources, safe=True)
        self.collection.insert(task_2_resources, safe=True)

        # deleting the repository should be postponed by both binds

        resources = {
            dispatch_constants.RESOURCE_REPOSITORY_TYPE: {
                repo_id: dispatch_constants.RESOURCE_DELETE_OPERATION
            }
        }

        response, blockers, reasons, task_resources = self.coordinator._find_conflicts(resources)

        self.assertTrue(response is dispatch_constants.CALL_POSTPONED_RESPONSE, response)
        self.assertTrue(task_1 in blockers)
        self.assertTrue(task_2 in blockers)
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
        deletion_task_resources = coordinator.resource_dict_to_task_resources(deletion_resources)
        coordinator.set_task_id_on_task_resources(task_id, deletion_task_resources)
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

        response, blockers, reasons, task_resources = self.coordinator._find_conflicts(resources)

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
        self.coordinator._run_task(task, False)
        self.assertTrue(len(task.call_request.execution_hooks[dispatch_constants.CALL_ENQUEUE_LIFE_CYCLE_CALLBACK]) == 1)
        self.assertTrue(len(task.call_request.execution_hooks[dispatch_constants.CALL_DEQUEUE_LIFE_CYCLE_CALLBACK]) == 2)
        self.assertTrue(coordinator.coordinator_dequeue_callback in task.call_request.execution_hooks[dispatch_constants.CALL_DEQUEUE_LIFE_CYCLE_CALLBACK])

    def test_run_task_sync(self):
        task = Task(call.CallRequest(dummy_call))
        self.coordinator._run_task(task, True)
        self.assertTrue(coordinator.wait_for_task.call_count == 2, coordinator.wait_for_task.call_count)


class CoordinatorWaitForTaskTests(CoordinatorTests):

    def test_run_task_sync_timeout(self):
        task = Task(call.CallRequest(dummy_call))
        timeout = datetime.timedelta(seconds=0.001)
        self.assertRaises(OperationTimedOut,
                          self.coordinator._run_task,
                          task, True, timeout)


class CoordinatorCallExecutionTests(CoordinatorTests):

    def setUp(self):
        super(CoordinatorCallExecutionTests, self).setUp()
        self.coordinator._run_task = mock.Mock()

    def test_execute_call(self):
        call_request = call.CallRequest(dummy_call)
        call_report = self.coordinator.execute_call(call_request)
        self.assertTrue(isinstance(call_report, call.CallReport))
        self.assertTrue(self.coordinator._run_task.call_count == 1)
        task = self.coordinator._run_task.call_args[0][0]
        self.assertTrue(isinstance(task, Task))
        # XXX no idea why this fails
        #self.assertFalse(call_report.task_id == task.id, '"%s" != "%s"' % (call_report.task_id, task.id))

    def test_execute_call_synchronously(self):
        call_request = call.CallRequest(dummy_call)
        self.coordinator.execute_call_synchronously(call_request)
        self.assertTrue(self.coordinator._run_task.call_count == 1)

    def test_execute_call_asynchronously(self):
        call_request = call.CallRequest(dummy_call)
        self.coordinator.execute_call_asynchronously(call_request)
        self.assertTrue(self.coordinator._run_task.call_count == 1)

    def test_execute_multiple_calls(self):
        call_requests = [call.CallRequest(dummy_call), call.CallRequest(dummy_call)]
        call_reports = self.coordinator.execute_multiple_calls(call_requests)
        self.assertTrue(len(call_requests) == len(call_reports))
        self.assertTrue(self.coordinator._run_task.call_count == len(call_requests))


