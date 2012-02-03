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
import time
import types

from pulp.server.db.model.dispatch import TaskResource
from pulp.server.dispatch import call
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import exceptions as dispatch_exceptions
from pulp.server.dispatch.task import Task
from pulp.server.dispatch.taskqueue import TaskQueue

# coordinator class ------------------------------------------------------------

class Coordinator(object):

    def __init__(self, task_queue, task_wait_sleep_interval=0.5):
        assert isinstance(task_queue, TaskQueue)

        self.task_queue = task_queue
        self.task_resource_collection = TaskResource.get_collection()
        self.task_wait_sleep_interval = task_wait_sleep_interval

    # execution methods --------------------------------------------------------

    def run_task(self, call_request):
        pass

    def run_task_synchronously(self, call_request, timeout=None):
        pass

    def run_task_asynchronously(self, call_request):
        pass

    def run_job(self, call_request_list):
        pass

    # conflict resolution algorithm --------------------------------------------

    def _find_conflicts(self, resources):
        postponing_tasks = set()
        postponing_reasons = []
        rejecting_tasks = set()
        rejecting_reasons = []

        task_resources = resource_dict_to_task_resources(resources)
        or_query = filter_dicts(task_resources, ('resource_type', 'resource_id'))
        cursor = self.task_resource_collection.find({'$or': or_query})

        for task_resource in cursor:
            proposed_operations = resources[task_resource['resource_type']][task_resource['resource_id']]
            for operation in proposed_operations:
                postponing_operations = get_postponing_operations(operation)
                rejecting_operations = get_rejecting_operations(operation)
                for current_operation in task_resource['operations']:
                    if current_operation in postponing_operations:
                        postponing_tasks.add(task_resource['task_id'])
                        reason = filter_dicts([task_resource], ('resource_type', 'resource_id'))[0]
                        reason['operation'] = current_operation
                        postponing_reasons.append(reason)
                    if current_operation in rejecting_operations:
                        rejecting_tasks.add(task_resource['task_id'])
                        reason = filter_dicts([task_resource], ('resource_type', 'resource_id'))[0]
                        reason['operation'] = current_operation
                        rejecting_reasons.append(reason)

        if rejecting_tasks:
            return dispatch_constants.CALL_REJECTED_RESPONSE, rejecting_tasks, rejecting_reasons, task_resources
        if postponing_tasks:
            return dispatch_constants.CALL_POSTPONED_RESPONSE, postponing_tasks, postponing_reasons, task_resources
        return dispatch_constants.CALL_ACCEPTED_RESPONSE, set(), [], task_resources

    # query methods ------------------------------------------------------------

    def find_call_reports(self, **criteria):
        pass

    # control methods ----------------------------------------------------------

    def cancel_task(self, task_id):
        pass

    def cancel_job(self, job_id):
        pass

# utility functions ------------------------------------------------------------

def filter_dicts(dicts, fields):
    """
    Filter an iterable a dicts, returning dicts that only have the keys and
    corresponding values for the passed in fields.
    @param dicts: iterable of dicts to filter
    @type  dicts: iterable of dicts
    @param fields: iterable of keys to retain
    @type  fields: iterable
    @return: list of dicts with keys only found in the passed in fields
    @rtype:  list of dicts
    """
    filtered_dicts = []
    for d in dicts:
        n = {}
        for f in fields:
            n[f] = d[f]
        filtered_dicts.append(n)
    return filtered_dicts


def get_postponing_operations(operation):
    """
    Get a list of operations that will postpone the passed in operation
    @param operation: proposed operation
    @type  operation: str
    @return: (possibly empty) list of operations
    @rtype:  list
    """
    postponing = []
    for op, operation_responses in dispatch_constants.RESOURCE_OPERATIONS_MATRIX.items():
        response = operation_responses[operation]
        if response is dispatch_constants.CALL_POSTPONED_RESPONSE:
            postponing.append(op)
    return postponing


def get_rejecting_operations(operation):
    """
    Get a list of operations that will reject the passed in operation
    @param operation: proposed operation
    @type  operation: str
    @return: (possibly empty) list of operations
    @rtype:  list
    """
    rejecting = []
    for op, operation_responses in dispatch_constants.RESOURCE_OPERATIONS_MATRIX.items():
        response = operation_responses[operation]
        if response is dispatch_constants.CALL_REJECTED_RESPONSE:
            rejecting.append(op)
    return rejecting


def resource_dict_to_task_resources(resource_dict):
    """
    Convert a resources dictionary to a list of task resource instances
    @param resource_dict: dict in the form of {resource_type: {resource_id: [operations list]}}
    @type  resource_dict: dict
    @return: list of task resource objects pertaining to the values of the resource_dict
    @rtype:  list of L{TaskResource} instances
    """
    task_resources = []
    for resource_type, resource_operations in resource_dict.items():
        for resource_id, operations in resource_operations.items():
            task_resource = TaskResource(None, resource_type, resource_id, operations)
            task_resources.append(task_resource)
    return task_resources


def set_task_id_on_task_resources(task_id, task_resources):
    """
    Set the task_id field on an iterable of task resources.
    @param task_id: task_id field value
    @param task_resources: iterable of task resources to set task_id on
    @type  task_resources: iterable of L{TaskResource} instances
    """
    for task_resource in task_resources:
        task_resource['task_id'] = task_id


def wait_for_task(task, states, sleep_interval=0.5, timeout=None):
    """
    Wait for a task to be in a certain set of states
    @param task: task to wait for
    @type  task: L{Task}
    @param states: set of valid states
    @type  states: list, set, or tuple
    @param sleep_interval: time, in seconds, to wait in between polling the task
    @type  sleep_interval: float or int
    @param timeout: maximum amount of time to poll task, None means indefinitely
    @type  timeout: None or datetime.timedelta
    """
    assert isinstance(task, Task)
    assert isinstance(states, (list, set, tuple))
    assert isinstance(sleep_interval, (float, int))
    assert isinstance(timeout, (datetime.timedelta, types.NoneType))

    start = datetime.datetime.now()
    while task.call_report.state not in states:
        time.sleep(sleep_interval)
        if timeout is None:
            continue
        now = datetime.datetime.now()
        if now - start < timeout:
            continue
        # TODO raise error instead of break
        break

# coordinator callbacks --------------------------------------------------------

def coordinator_complete_callback(call_request, call_report):
    """
    Callback to be executed upon call completion that will clean up the
    coordinator's accounting data pertaining to the call.
    @param call_request: call request for the call
    @type  call_request: L{call.CallRequest} instance
    @param call_report: call report for the call
    @type  call_report: L{call.CallReport} instance
    """
    # yes, I know that the call_request is not being used
    task_id = call_report.task_id
    collection = TaskResource.get_collection()
    collection.remove({'task_id': task_id}, safe=True)

