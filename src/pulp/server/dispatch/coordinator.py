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
import uuid

from pulp.server.db.model.dispatch import TaskResource
from pulp.server.dispatch import call
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import exceptions as dispatch_exceptions
from pulp.server.dispatch.task import AsyncTask, Task
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
        call_report = self._run_task(call_request, Task)
        return call_report

    def run_task_synchronously(self, call_request, timeout=None):
        call_report = self._run_task(call_request, Task, True, timeout)
        return call_report

    def run_task_asynchronously(self, call_request):
        call_report = self._run_task(call_request, Task, False)
        return call_report

    def run_asynchronous_task(self, call_request):
        call_report = self._run_task(call_request, AsyncTask, False)
        return call_report

    def run_job(self, call_request_list):
        job_id = self._generate_job_id()
        call_report_list = []
        for call_request in call_request_list:
            call_request.tags.append(job_id)
            call_report = self._run_task(call_request, Task, False)
            call_report.job_id = job_id
            call_report_list.append(call_report)
        return call_report_list

    def run_asynchronous_job(self, call_request_list):
        job_id = self._generate_job_id()
        call_report_list = []
        for call_request in call_request_list:
            call_request.tags.append(job_id)
            call_report = self._run_task(call_request, AsyncTask, False)
            call_report.job_id = job_id
            call_report_list.append(call_report)
        return call_report_list

    # execution utilities ------------------------------------------------------

    def _run_task(self, call_request, task_class, synchronous=None, timeout=None):
        """
        Run a task.
        @param call_request: call request to run in the task queue
        @type  call_request: L{call.CallRequest}
        @param task_class: task class to run task in
        @type  task_class: L{Task}
        @param synchronous: whether or not to run the task synchronously,
                            None means dependent on what the conflict response is
        @type  synchronous: None or bool
        @param timeout: how much time to wait for a synchronous task to start
                        None means indefinitely
        @type  timeout: None or datetime.timedelta
        @return: a call report for the call request
        @rtype:  L{call.CallReport}
        """
        self.task_queue.lock()
        try:
            call_request.add_execution_hook(dispatch_constants.CALL_COMPLETE_EXECUTION_HOOK, coordinator_complete_callback)
            call_report = call.CallReport()
            response, blocking, reasons, task_resources = self._find_conflicts(call_request.resources)
            call_report.response = response
            call_report.reason = reasons
            if response is dispatch_constants.CALL_REJECTED_RESPONSE:
                return call_report
            task = task_class(call_request, call_report)
            call_report.task_id = task.id
            task.blocking_tasks = blocking
            set_task_id_on_task_resources(task.id, task_resources)
            self.task_resource_collection.insert(task_resources, safe=True)
            self.task_queue.enqueue(task)
        finally:
            self.task_queue.unlock()

        if synchronous or (synchronous is None and response is dispatch_constants.CALL_ACCEPTED_RESPONSE):
            try:
                wait_for_task(task, [dispatch_constants.CALL_RUNNING_STATE], timeout=timeout)
            except dispatch_exceptions.SynchronousCallTimeoutError:
                self.task_queue.dequeue(task)
                raise
            else:
                wait_for_task(task, dispatch_constants.CALL_COMPLETE_STATES)
        return call_report

    def _generate_job_id(self):
        self.task_queue.lock()
        try:
            job_id = uuid.uuid4()
            return job_id
        finally:
            self.task_queue.unlock()

    # conflict resolution algorithm --------------------------------------------

    def _find_conflicts(self, resources):
        """
        Find conflicting tasks, if any, and provide the following:
        * a task response, (accepted, postponed, rejected)
        * a (possibly empty) set of blocking task ids
        * a list of blocking "reasons" in the form of TaskResource instances
        * a list of task resources corresponding to the given resources
        @param resources: dictionary of resources and their proposed operations
        @type  resources: dict
        @return: tuple of objects described above
        @rtype:  tuple
        """
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

# conflict detection utility functions -----------------------------------------

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

# call run utility functions ---------------------------------------------------

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
        raise dispatch_exceptions.SynchronousCallTimeoutError(str(task))

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

