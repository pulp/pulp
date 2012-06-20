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
import datetime
import sys
import time
import types
import uuid

from pulp.server.auth.authorization import (
    GrantPermmissionsForTaskV2, RevokePermissionsForTaskV2)
from pulp.server.db.model.dispatch import QueuedCall, TaskResource
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import exceptions as dispatch_exceptions
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.dispatch import history as dispatch_history
from pulp.server.dispatch.call import CallRequest
from pulp.server.dispatch.task import AsyncTask, Task
from pulp.server.exceptions import OperationTimedOut
from pulp.server.util import NoTopologicalOrderingExists, topological_sort

# coordinator class ------------------------------------------------------------

class Coordinator(object):
    """
    Coordinator class that runs call requests in the task queue and detects and
    resolves conflicting operations on resources.
    @ivar task_state_poll_interval: sleep interval to use while polling a "synchronous" task
    @type task_state_poll_interval: float
    """

    def __init__(self, task_state_poll_interval=0.5):

        self.task_state_poll_interval = task_state_poll_interval

    # explicit initialization --------------------------------------------------

    def start(self):
        """
        Start the coordinator by clearing conflict metadata and restarting any
        interrupted tasks.
        """
        # drop all previous knowledge of running tasks
        task_resource_collection = TaskResource.get_collection()
        task_resource_collection.remove(safe=True)
        # re-start interrupted tasks
        queued_call_collection = QueuedCall.get_collection()
        queued_call_list = list(queued_call_collection.find().sort('timestamp'))
        queued_call_collection.remove(safe=True)
        for queued_call in queued_call_list:
            call_request = CallRequest.deserialize(queued_call['serialized_call_request'])
            call_report = self.execute_call_asynchronously(call_request)
            # TODO log rejected calls?

    # execution methods --------------------------------------------------------

    def execute_call(self, call_request, call_report=None):
        """
        Execute a call request in the tasking sub-system.
        This will run the task synchronously if no conflicts are detected,
        asynchronously if there are tasks that will postpone this one.
        @param call_request: call request to run
        @type  call_request: L{call.CallRequest} instance
        @param call_report: call report for call request
        @type  call_report: L{call.CallReport} instance or None
        @return: call report pertaining to the running of the request call
        @rtype:  L{call.CallReport} instance
        """
        task = self._create_task(call_request, call_report)
        synchronous = None
        if isinstance(task, AsyncTask):
            synchronous = False
        self._run_task(task, synchronous)
        return copy.copy(task.call_report)

    def execute_call_synchronously(self, call_request, call_report=None, timeout=None):
        """
        Execute a call request in the tasking sub-system.
        This will run the task synchronously regardless of postponing conflicts.
        NOTE: this method cannot be used to execute asynchronous tasks.
        @param call_request: call request to run
        @type  call_request: L{call.CallRequest} instance
        @param call_report: call report for call request
        @type  call_report: L{call.CallReport} instance or None
        @param timeout: maximum amount of time to wait for the task to start
        @type  timeout: None or datetime.timedelta
        @return: call report pertaining to the running of the request call
        @rtype:  L{call.CallReport} instance
        """
        assert isinstance(timeout, (datetime.timedelta, types.NoneType))
        task = self._create_task(call_request, call_report)
        if isinstance(task, AsyncTask):
            raise dispatch_exceptions.AsynchronousExecutionError('asynchronous')
        self._run_task(task, True, timeout)
        return copy.copy(task.call_report)

    def execute_call_asynchronously(self, call_request, call_report=None):
        """
        Execute a call request in the tasking sub-system.
        This will run the task asynchronously regardless of no postponing conflicts.
        @param call_request: call request to run
        @type  call_request: L{call.CallRequest} instance
        @param call_report: call report for call request
        @type  call_report: L{call.CallReport} instance or None
        @return: call report pertaining to the running of the request call
        @rtype:  L{call.CallReport} instance
        """
        task = self._create_task(call_request, call_report)
        self._run_task(task, False)
        return copy.copy(task.call_report)

    def execute_multiple_calls(self, call_request_list):
        """
        Execute a list of call requests in the tasking sub-system.
        This will run the tasks asynchronously regardless of postponing conflicts.
        @param call_request_list: call requests to run
        @type  call_request_list: list of L{call.CallRequest} instances
        @return: list of call reports pertaining to the running of the request calls
        @rtype:  list of L{call.CallReport} instances
        """
        task_group_id = self._generate_task_group_id()
        task_list = []
        call_report_list = []
        for call_request in call_request_list:
            task = self._create_task(call_request, task_group_id=task_group_id)
            task_list.append(task)
        sorted_task_list = self._analyze_dependencies(task_list)
        for task in sorted_task_list:
            self._run_task(task, False)
            call_report_list.append(copy.copy(task.call_report))
        return call_report_list

    # execution utilities ------------------------------------------------------

    def _create_task(self, call_request, call_report=None, task_group_id=None):
        """
        Create the task for the given call request.
        @param call_request: call request to encapsulate in a task
        @type  call_request: L{call.CallRequest} instance
        @param call_report: call report for call request
        @type  call_report: L{call.CallReport} instance or None
        @param task_group_id: optional task group id
        @type  task_group_id: None or str
        @return: task that encapsulates the call request
        @rtype:  L{Task} instance
        """
        if not call_request.asynchronous:
            task = Task(call_request, call_report)
        else:
            task = AsyncTask(call_request, call_report)
        task.call_report.task_id = task.id
        task.call_report.task_group_id = task_group_id
        return task

    def _run_task(self, task, synchronous=None, timeout=None):
        """
        Run a task.
        @param task: task to run
        @type  task: L{Task} instance
        @param synchronous: whether or not to run the task synchronously,
                            None means dependent on what the conflict response is
        @type  synchronous: None or bool
        @param timeout: how much time to wait for a synchronous task to start
                        None means indefinitely
        @type  timeout: None or datetime.timedelta
        """
        # we have to lock the task queue here as there is a race condition
        # between calculating the blocking/postponing tasks and enqueueing the
        # task when 2 or more tasks are being run that may have
        # interdependencies
        task_queue = dispatch_factory._task_queue()
        task_queue.lock()
        task_resource_collection = TaskResource.get_collection()
        try:
            response, blocking, reasons, task_resources = self._find_conflicts(task.call_request.resources)
            task.call_report.response = response
            task.call_report.reasons = reasons
            if response is dispatch_constants.CALL_REJECTED_RESPONSE:
                return
            task.blocking_tasks.update(blocking)
            task.call_request.add_life_cycle_callback(dispatch_constants.CALL_ENQUEUE_LIFE_CYCLE_CALLBACK, GrantPermmissionsForTaskV2())
            task.call_request.add_life_cycle_callback(dispatch_constants.CALL_DEQUEUE_LIFE_CYCLE_CALLBACK, RevokePermissionsForTaskV2())
            task.call_request.add_life_cycle_callback(dispatch_constants.CALL_DEQUEUE_LIFE_CYCLE_CALLBACK, coordinator_dequeue_callback)
            if task_resources:
                set_task_id_on_task_resources(task.id, task_resources)
                task_resource_collection.insert(task_resources, safe=True)
            task_queue.enqueue(task)
        finally:
            task_queue.unlock()

        # if the call has requested synchronous execution or can be
        # synchronously executed, do so
        if synchronous or (synchronous is None and response is dispatch_constants.CALL_ACCEPTED_RESPONSE):
            try:
                # it's perfectly legitimate for the call to complete before the fist poll
                running_states = [dispatch_constants.CALL_RUNNING_STATE]
                running_states.extend(dispatch_constants.CALL_COMPLETE_STATES)
                wait_for_task(task, running_states, poll_interval=self.task_state_poll_interval, timeout=timeout)
            except OperationTimedOut:
                task_queue.dequeue(task)
                raise
            else:
                wait_for_task(task, dispatch_constants.CALL_COMPLETE_STATES,
                              poll_interval=self.task_state_poll_interval)

    def _generate_task_group_id(self):
        """
        Generate a unique task group id.
        @return: uuid string
        @rtype:  str
        """
        # NOTE this needs to utilize a central locking mechanism because on
        # Python < 2.5 the uuid package can generate non-unique ids if more than
        # one thread accesses it at a time
        task_queue = dispatch_factory._task_queue()
        task_queue.lock()
        try:
            task_group_id = str(uuid.uuid4())
            return task_group_id
        finally:
            task_queue.unlock()

    # user-defined dependencies ------------------------------------------------

    def _analyze_dependencies(self, task_list):
        # build a dependency graph to check the user-defined dependencies
        call_request_map = dict((task.call_request.id, task) for task in task_list)
        dependency_graph = {}
        for task in task_list:
            dependency_graph[task] = [call_request_map[id] for id in task.call_request.dependencies]
        # check the dependencies with a topological sort
        try:
            sorted_task_list = topological_sort(dependency_graph)
        except NoTopologicalOrderingExists:
            raise dispatch_exceptions.CircularDependencies(), None, sys.exc_info()[2]
        # add the dependencies as actual blocking tasks
        for task in sorted_task_list:
            dependency_tasks = [call_request_map[id].id for id in task.call_request.dependencies]
            task.blocking_tasks.update(dependency_tasks)
        return sorted_task_list

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
        if not resources:
            return dispatch_constants.CALL_ACCEPTED_RESPONSE, set(), [], []

        postponing_tasks = set()
        postponing_reasons = []
        rejecting_tasks = set()
        rejecting_reasons = []

        task_resource_collection = TaskResource.get_collection()
        task_resources = resource_dict_to_task_resources(resources)
        or_query = filter_dicts(task_resources, ('resource_type', 'resource_id'))
        cursor = task_resource_collection.find({'$or': or_query})

        for task_resource in cursor:
            proposed_operation = resources[task_resource['resource_type']][task_resource['resource_id']]
            postponing_operations = get_postponing_operations(proposed_operation)
            rejecting_operations = get_rejecting_operations(proposed_operation)
            current_operation = task_resource['operation']
            if current_operation in postponing_operations:
                postponing_tasks.add(task_resource['task_id'])
                reason = filter_dicts([task_resource], ('resource_type', 'resource_id'))[0]
                reason['operation'] = current_operation
                if reason not in postponing_reasons:
                    postponing_reasons.append(reason)
            if current_operation in rejecting_operations:
                rejecting_tasks.add(task_resource['task_id'])
                reason = filter_dicts([task_resource], ('resource_type', 'resource_id'))[0]
                reason['operation'] = current_operation
                if reason not in rejecting_reasons:
                    rejecting_reasons.append(reason)

        if rejecting_tasks:
            return dispatch_constants.CALL_REJECTED_RESPONSE, rejecting_tasks, rejecting_reasons, task_resources
        if postponing_tasks:
            return dispatch_constants.CALL_POSTPONED_RESPONSE, postponing_tasks, postponing_reasons, task_resources
        return dispatch_constants.CALL_ACCEPTED_RESPONSE, set(), [], task_resources

    # query methods ------------------------------------------------------------

    def find_tasks(self, **criteria):
        """
        Find call reports that match the criteria given as key word arguments.

        Supported criteria:
         * task_id
         * task_group_id
         * state
         * call_name
         * class_name
         * args
         * kwargs
         * resources
         * tags
        """
        valid_criteria = set(('task_id', 'task_group_id', 'state', 'call_name',
                              'class_name', 'args', 'kwargs', 'resources', 'tags'))
        provided_criteria = set(criteria.keys())
        superfluous_criteria = provided_criteria - valid_criteria
        if superfluous_criteria:
            raise dispatch_exceptions.UnrecognizedSearchCriteria(*list(superfluous_criteria))
        tasks = []
        task_queue = dispatch_factory._task_queue()
        for task in task_queue.all_tasks():
            if task_matches_criteria(task, criteria):
                tasks.append(task)
        return tasks

    def find_call_reports(self, **criteria):
        """
        Find call reports that match the criteria given as key word arguments.

        Supported criteria:
         * task_id
         * task_group_id
         * state
         * call_name
         * class_name
         * args
         * kwargs
         * resources
         * tags
        """
        tasks = self.find_tasks(**criteria)
        call_reports = [t.call_report for t in tasks]
        # XXX should we be appending history here?
        #for archived_call in dispatch_history.find_archived_calls(**criteria):
        #    call_reports.append(archived_call['serialized_call_report'])
        return call_reports

    # control methods ----------------------------------------------------------

    def complete_call_success(self, task_id, result=None):
        task_list = self.find_tasks(task_id=task_id)
        if not task_list:
            # XXX raise an error
            return None
        task = task_list[0]
        task._succeeded(result)

    def complete_call_failure(self, task_id, exception=None, traceback=None):
        task_list = self.find_tasks(task_id=task_id)
        if not task_list:
            # XXX raise an error
            return None
        task = task_list[0]
        task._failed(exception, traceback)

    def cancel_call(self, task_id):
        """
        Cancel a call request using the task id.
        @param task_id: task id for call request to cancel
        @type  task_id: str
        @return: True if the task is being cancelled, False if not, or None if the task was not found
        @rtype:  bool or None
        """
        task_queue = dispatch_factory._task_queue()
        task = task_queue.get(task_id)
        if task is None:
            return None
        return task_queue.cancel(task)

    def cancel_multiple_calls(self, task_group_id):
        """
        Cancel multiple call requests using the task_group id.
        @param task_group_id: task_group id for multiple calls
        @type  task_group_id: str
        @return: dictionary of {task id: cancel return} for tasks associated with the task_group id
        @rtype:  dict
        """
        cancel_returns = {}
        task_queue = dispatch_factory._task_queue()
        for task in task_queue.all_tasks():
            if task_group_id != task.call_report.task_group_id:
                continue
            cancel_returns[task.id] = task_queue.cancel(task)
        return cancel_returns

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
        for resource_id, operation in resource_operations.items():
            task_resource = TaskResource(None, resource_type, resource_id, operation)
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


def wait_for_task(task, states, poll_interval=0.5, timeout=None):
    """
    Wait for a task to be in a certain set of states
    @param task: task to wait for
    @type  task: L{Task}
    @param states: set of valid states
    @type  states: list, set, or tuple
    @param poll_interval: time, in seconds, to wait in between polling the task
    @type  poll_interval: float or int
    @param timeout: maximum amount of time to poll task, None means indefinitely
    @type  timeout: None or datetime.timedelta
    """
    assert isinstance(task, Task)
    assert isinstance(states, (list, set, tuple))
    assert isinstance(poll_interval, (float, int))
    assert isinstance(timeout, (datetime.timedelta, types.NoneType))

    start = datetime.datetime.now()
    while task.call_report.state not in states:
        time.sleep(poll_interval)
        if timeout is None:
            continue
        now = datetime.datetime.now()
        if now - start < timeout:
            continue
        raise OperationTimedOut(timeout)

# query utility functions ------------------------------------------------------

def task_matches_criteria(task, criteria):
    """
    Test a task to see if it matches the given search criteria.
    @param task: task to test
    @type  task: pulp.server.dispatch.task.Task
    @param criteria: search criteria to match
    @type  criteria: dict
    @return: True if the task matches, False otherwise
    @rtype:  bool
    """
    if 'task_id' in criteria and criteria['task_id'] != task.call_report.task_id:
        return False
    if 'task_group_id' in criteria and criteria['task_group_id'] != task.call_report.task_group_id:
        return False
    if 'state' in criteria and criteria['state'] != task.call_report.state:
        return False
    if 'call_name' in criteria and dispatch_history.callable_name(criteria.get('class_name'), criteria['call_name']) != task.call_request.callable_name():
        return False
    for a in criteria.get('args', []):
        if a not in task.call_request.args:
            return False
    for k, v in criteria.get('kwargs', {}):
        if k not in task.call_request.kwargs or v != task.call_request.kwargs[k]:
            return False
    for t in criteria.get('tags', []):
        if t not in task.call_request.tags:
            return False
    return True

# coordinator callbacks --------------------------------------------------------

def coordinator_dequeue_callback(call_request, call_report):
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

