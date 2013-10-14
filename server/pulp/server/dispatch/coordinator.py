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
import logging
import time
import types
import uuid
from gettext import gettext as _

from pulp.server.auth.authorization import (
    GrantPermmissionsForTaskV2, RevokePermissionsForTaskV2)
from pulp.server.db.model.dispatch import QueuedCall, CallResource
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import exceptions as dispatch_exceptions
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.dispatch.call import CallRequest
from pulp.server.dispatch.task import AsyncTask, Task
from pulp.server.exceptions import OperationTimedOut
from pulp.server.util import subdict, TopologicalSortError, topological_sort


logger = logging.getLogger(__name__)

_VALID_SEARCH_CRITERIA = frozenset(('call_request_id', 'call_request_group_id',
                                    'call_request_id_list', 'schedule_id',
                                    'state', 'callable_name', 'args', 'kwargs',
                                    'resources', 'tags'))


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
        self.call_resource_collection = CallResource.get_collection()

    # explicit initialization --------------------------------------------------

    def start(self):
        """
        Start the coordinator by clearing conflicting metadata and restarting any
        interrupted tasks.
        """
        # drop all previous knowledge of previous calls
        self.call_resource_collection.remove(safe=True)

        # re-start interrupted tasks
        queued_call_collection = QueuedCall.get_collection()
        queued_call_list = list(queued_call_collection.find().sort('timestamp'))
        queued_call_collection.remove(safe=True)

        queued_call_request_list = [c for c in
                                    [CallRequest.deserialize(q['serialized_call_request']) for q in queued_call_list]
                                    if c is not None]

        while queued_call_request_list:
            call_request = queued_call_request_list[0]

            # individually call un-grouped calls
            if call_request.group_id is None:
                queued_call_request_list.remove(call_request)
                self.execute_call_asynchronously(call_request)
                continue

            # call grouped calls at all at once
            call_request_group = [c for c in queued_call_request_list if c.group_id == call_request.group_id]
            map(queued_call_request_list.remove, call_request_group)

            try:
                # NOTE (jconnor 2012-10-12) this will change the group_id, but I don't think I care
                self.execute_multiple_calls(call_request_group)
            except TopologicalSortError, e:
                log_msg = _('Cannot execute call request group: %(g)s' % {'g': call_request.group_id})
                logger.warn('\n'.join((log_msg, str(e))))

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
        self._process_tasks([task])

        if not isinstance(task, AsyncTask) and task.call_report.response is dispatch_constants.CALL_ACCEPTED_RESPONSE:
            self._run_task(task)

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
            raise dispatch_exceptions.AsynchronousExecutionError(['asynchronous'])

        self._process_tasks([task])

        if task.call_report.response is not dispatch_constants.CALL_REJECTED_RESPONSE:
            self._run_task(task, timeout)

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
        self._process_tasks([task])

        return copy.copy(task.call_report)

    def execute_multiple_calls(self, call_request_list):
        """
        Execute a list of call requests in the tasking sub-system.
        This will run the tasks asynchronously regardless of postponing conflicts.
        @param call_request_list: call requests to run
        @type  call_request_list: list of L{call.CallRequest} instances
        @return: list of call reports pertaining to the running of the request calls
        @rtype:  list of L{call.CallReport} instances
        @raise: L{TopologicalSortError} if inter-task dependencies are malformed
        """
        group_id = self._generate_call_request_group_id()
        task_list = [self._create_task(c, None, group_id) for c in call_request_list]
        sorted_task_list = self._analyze_dependencies(task_list)
        self._process_tasks(sorted_task_list)
        return [t.call_report for t in sorted_task_list]

    # execution utilities ------------------------------------------------------

    def _create_task(self, call_request, call_report=None, call_request_group_id=None):
        """
        Create the task for the given call request.
        @param call_request: call request to encapsulate in a task
        @type  call_request: L{call.CallRequest} instance
        @param call_report: call report for call request
        @type  call_report: L{call.CallReport} instance or None
        @param call_request_group_id: optional call request group id
        @type  call_request_group_id: None or str
        @return: task that encapsulates the call request
        @rtype:  L{Task} instance
        """
        if call_request_group_id is not None:
            call_request.group_id = call_request_group_id

        if not call_request.asynchronous:
            task = Task(call_request, call_report)
        else:
            task = AsyncTask(call_request, call_report)

        return task

    def _process_tasks(self, task_list):
        """
        Look for, and potentially resolve, resource conflicts for and enqueue
        the tasks in the task list.
        @param task_list: list of tasks tasks to work the coordinator magic on
        @type  task_list: list
        """

        # we have to lock the task queue here as there is a race condition
        # between calculating the blocking/postponing tasks and enqueueing the
        # task when 2 or more tasks are being run that may have interdependencies

        task_queue = dispatch_factory._task_queue()
        task_queue.lock()

        responses_list = []
        call_resource_list = []

        try:
            for task in task_list:
                response, blocking, reasons, call_resources = self._find_conflicts(task.call_request.resources)
                task.call_report.response = response
                task.call_report.reasons = reasons

                responses_list.append(response)

                if response is dispatch_constants.CALL_REJECTED_RESPONSE:
                    continue

                dependencies = dict.fromkeys(blocking, dispatch_constants.CALL_COMPLETE_STATES)
                # use the original (possibly more restrictive) values, when present
                dependencies.update(task.call_request.dependencies)
                task.call_request.dependencies = dependencies

                task.call_request.add_life_cycle_callback(dispatch_constants.CALL_ENQUEUE_LIFE_CYCLE_CALLBACK, GrantPermmissionsForTaskV2())
                task.call_request.add_life_cycle_callback(dispatch_constants.CALL_DEQUEUE_LIFE_CYCLE_CALLBACK, RevokePermissionsForTaskV2())
                task.call_request.add_life_cycle_callback(dispatch_constants.CALL_DEQUEUE_LIFE_CYCLE_CALLBACK, coordinator_dequeue_callback)

                if call_resources:
                    set_call_request_id_on_call_resources(task.call_request.id, call_resources)
                    call_resource_list.extend(call_resources)

            # for a call request group: if 1 of the tasks is rejected, then they are all rejected
            if reduce(lambda p, r: r is dispatch_constants.CALL_REJECTED_RESPONSE or p, responses_list, False):
                map(lambda t: setattr(t.call_report, 'response', dispatch_constants.CALL_REJECTED_RESPONSE), task_list)
                return

            if call_resource_list:
                self.call_resource_collection.insert(call_resource_list, safe=True)

            for task in task_list:
                task_queue.enqueue(task)

        finally:
            task_queue.unlock()

    def _run_task(self, task, timeout=None):
        """
        Run a task "synchronously".
        @param task: task to run
        @type  task: L{Task} instance
        @param timeout: how much time to wait for a synchronous task to start
                        None means indefinitely
        @type  timeout: None or datetime.timedelta
        """
        task_queue = dispatch_factory._task_queue()
        valid_states = [dispatch_constants.CALL_RUNNING_STATE]
        # it's perfectly legitimate for the call to complete before the first poll
        valid_states.extend(dispatch_constants.CALL_COMPLETE_STATES)

        try:
            wait_for_task(task, valid_states, poll_interval=self.task_state_poll_interval, timeout=timeout)

        except OperationTimedOut:
            task_queue.dequeue(task) # dequeue or cancel? really need timed out support
            raise

        else:
            wait_for_task(task, dispatch_constants.CALL_COMPLETE_STATES,
                          poll_interval=self.task_state_poll_interval)

    def _generate_call_request_group_id(self):
        """
        Generate a unique call request group id.
        @return: uuid string
        @rtype:  str
        """
        # NOTE this needs to utilize a central locking mechanism because on
        # Python < 2.5 the uuid package can generate non-unique ids if more than
        # one thread accesses it at a time
        task_queue = dispatch_factory._task_queue()
        task_queue.lock()
        try:
           return str(uuid.uuid4())
        finally:
            task_queue.unlock()

    # user-defined dependencies ------------------------------------------------

    def _analyze_dependencies(self, task_list):
        """
        Analyze and validate the user-defined dependencies among a list of tasks.
        @param task_list: list of tasks
        @type task_list: list
        @return: sorted task list
        @rtype: list
        """

        call_request_map = dict((task.call_request.id, task) for task in task_list)
        dependency_graph = dict((task.call_request.id, task.call_request.dependencies.keys()) for task in task_list)

        # check the dependencies with a topological sort and get a valid order
        # in which to enqueue the tasks

        sorted_call_request_ids = topological_sort(dependency_graph)

        sorted_task_list = [call_request_map[id] for id in sorted_call_request_ids]
        return sorted_task_list

    def _find_conflicts(self, resources):
        """
        Find conflicting tasks, if any, and provide the following:
        * a task response, (accepted, postponed, rejected)
        * a (possibly empty) set of blocking call request ids
        * a list of blocking "reasons" in the form of TaskResource instances
        * a list of task resources corresponding to the given resources

        @param resources: dictionary of resources and their proposed operations
        @type  resources: dict
        @return: tuple of objects described above
        @rtype:  tuple
        """
        if not resources:
            return dispatch_constants.CALL_ACCEPTED_RESPONSE, set(), [], []

        # Translate to the old format of resources with resource type and resource_id as a key
        # to make operation lookups easy in the conflict detection logic
        original_resources = resources
        resources = {}
        for operation, resource_dict in original_resources.items():
            for resource_type, resource_ids in resource_dict.items():
                for resource_id in resource_ids:
                    resources.setdefault(resource_type, {}).update({resource_id: operation})

        postponing_call_requests = set()
        postponing_reasons = []
        rejecting_call_requests = set()
        rejecting_reasons = []

        call_resources = resource_dict_to_call_resources(resources)
        or_query = filter_dicts(call_resources, ('resource_type', 'resource_id'))
        cursor = self.call_resource_collection.find({'$or': or_query})

        for call_resource in cursor:
            proposed_operation = resources[call_resource['resource_type']][call_resource['resource_id']]
            queued_operation = call_resource['operation']

            postponing_operations = get_postponing_operations(proposed_operation)

            if queued_operation in postponing_operations:
                postponing_call_requests.add(call_resource['call_request_id'])
                reason = filter_dicts([call_resource], ('resource_type', 'resource_id'))[0]
                reason['operation'] = queued_operation

                if reason not in postponing_reasons:
                    postponing_reasons.append(reason)

            rejecting_operations = get_rejecting_operations(proposed_operation)

            if queued_operation in rejecting_operations:
                rejecting_call_requests.add(call_resource['call_request_id'])
                reason = filter_dicts([call_resource], ('resource_type', 'resource_id'))[0]
                reason['operation'] = queued_operation

                if reason not in rejecting_reasons:
                    rejecting_reasons.append(reason)

        if rejecting_call_requests:
            return dispatch_constants.CALL_REJECTED_RESPONSE, rejecting_call_requests, rejecting_reasons, call_resources

        if postponing_call_requests:
            return dispatch_constants.CALL_POSTPONED_RESPONSE, postponing_call_requests, postponing_reasons, call_resources

        return dispatch_constants.CALL_ACCEPTED_RESPONSE, set(), [], call_resources

    # query methods ------------------------------------------------------------

    def get_call_reports_by_call_request_ids(self, call_request_id_list, include_completed=False):
        """
        Get all the call reports for corresponding to the given call request ids.
        @param call_request_id_list: list of call request ids
        @type: list or tuple
        @param include_completed: toggle inclusion of cached completed tasks
        @type include_completed: bool
        @return: list of call reports for all call request ids found in the task queue
        @rtype: list
        """
        task_queue = dispatch_factory._task_queue()

        if include_completed:
            queued_tasks = task_queue.all_tasks()
        else:
            queued_tasks = task_queue.incomplete_tasks()

        call_reports = []

        for task in queued_tasks:
            if task.call_request.id not in call_request_id_list:
                continue
            call_reports.append(task.call_report)

        return call_reports

    def _find_tasks(self, **criteria):
        """
        Find call reports that match the criteria given as key word arguments.

        Supported criteria:
         * call_request_id
         * call_request_group_id
         * call_request_id_list
         * schedule_id
         * state
         * callable_name
         * args
         * kwargs
         * resources
         * tags
        """
        provided_criteria = set(criteria.keys())

        superfluous_criteria = provided_criteria - _VALID_SEARCH_CRITERIA

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
         * call_request_id
         * call_request_group_id
         * call_request_id_list
         * schedule_id
         * state
         * callable_name
         * args
         * kwargs
         * resources
         * tags
        """
        tasks = self._find_tasks(**criteria)
        return [t.call_report for t in tasks]

    # control methods ----------------------------------------------------------

    def complete_call_success(self, call_request_id, result=None):
        """
        Report an asynchronous call's success.
        @param call_request_id: call request id of the asynchronous call
        @type call_request_id: str
        @param result: optional result of the successful call
        """
        task_list = self._find_tasks(call_request_id=call_request_id)
        if not task_list:
            return
        task = task_list[0]
        assert isinstance(task, AsyncTask)
        task._succeeded(result)

    def complete_call_failure(self, call_request_id, exception=None, traceback=None):
        """
        Report an asynchronous call's failure.
        @param call_request_id: call request id of the asynchronous call
        @type call_request_id: str
        @param exception: optional exception thrown during call
        @param traceback: optional traceback corresponding the exception
        """
        task_list = self._find_tasks(call_request_id=call_request_id)
        if not task_list:
            return
        task = task_list[0]
        assert isinstance(task, AsyncTask)
        task._failed(exception, traceback)

    def cancel_call(self, call_request_id):
        """
        Cancel a call request using the call request id.
        @param call_request_id: id for call request to cancel
        @type  call_request_id: str
        @return: True if the task is being cancelled, False if not, or None if the task was not found
        @rtype:  bool or None
        """
        task_queue = dispatch_factory._task_queue()
        task = task_queue.get(call_request_id)
        if task is None:
            return None
        return task_queue.cancel(task)

    def cancel_multiple_calls(self, call_request_group_id):
        """
        Cancel multiple call requests using the call request group id.
        @param call_request_group_id: call request group id for multiple calls
        @type  call_request_group_id: str
        @return: dictionary of {call request id: cancel return} for tasks associated with the call request group id
        @rtype:  dict
        """
        cancel_returns = {}
        task_queue = dispatch_factory._task_queue()
        for task in task_queue.all_tasks():
            if call_request_group_id != task.call_request.group_id:
                continue
            cancel_returns[task.call_request.id] = task_queue.cancel(task)
        return cancel_returns

    # progress reporting methods -----------------------------------------------

    def report_call_progress(self, call_request_id, progress):
        """
        Add a progress report to the task's call report.
        @param call_request_id: id for call to add progress report to
        @type call_request_id: str
        @param progress: progress report to add
        @type progress: dict
        """
        task_list = self._find_tasks(call_request_id=call_request_id)
        if not task_list:
            return
        task_list[0].call_report.progress = progress

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
        s = subdict(d, fields)
        filtered_dicts.append(s)
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


def resource_dict_to_call_resources(resource_dict):
    """
    Convert a resources dictionary to a list of task resource instances
    @param resource_dict: dict in the form of {resource_type: {resource_id: [operations list]}}
    @type  resource_dict: dict
    @return: list of call resource objects pertaining to the values of the resource_dict
    @rtype:  list of L{CallResource} instances
    """
    call_resources = []
    for resource_type, resource_operations in resource_dict.items():
        for resource_id, operation in resource_operations.items():
            call_resource = CallResource(None, resource_type, resource_id, operation)
            call_resources.append(call_resource)
    return call_resources

# call run utility functions ---------------------------------------------------

def set_call_request_id_on_call_resources(call_request_id, call_resources):
    """
    Set the task_id field on an iterable of task resources.
    @param call_request_id: task_id field value
    @param call_resources: iterable of task resources to set task_id on
    @type  call_resources: iterable of L{TaskResource} instances
    """
    for call_resource in call_resources:
        call_resource['call_request_id'] = call_request_id


def wait_for_task(task, states, poll_interval=0.5, timeout=None):
    """
    Wait for a task to be in a certain set of states
    @param task: task to wait for
    @type  task: L{Task}
    @param states: set of valid states
    @type  states: list or tuple
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
    if 'call_request_id' in criteria and criteria['call_request_id'] != task.call_request.id:
        return False
    if 'call_request_group_id' in criteria and criteria['call_request_group_id'] != task.call_request.group_id:
        return False
    if 'call_request_id_list' in criteria and task.call_request.id not in criteria['call_request_id_list']:
        return False
    if 'schedule_id' in criteria and criteria['schedule_id'] != task.call_report.schedule_id:
        return False
    if 'state' in criteria and criteria['state'] != task.call_report.state:
        return False
    if 'callable_name' in criteria and criteria['callable_name'] != task.call_request.callable_name():
        return False
    for a in criteria.get('args', []):
        if a not in task.call_request.args:
            return False
    for k, v in criteria.get('kwargs', {}).items():
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
    collection = CallResource.get_collection()
    collection.remove({'call_request_id': call_request.id}, safe=True)

