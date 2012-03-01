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
import time
import types
import uuid

from pulp.server.db.model.dispatch import TaskResource
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import exceptions as dispatch_exceptions
from pulp.server.dispatch import history as dispatch_history
from pulp.server.dispatch.call import CallReport
from pulp.server.dispatch.task import AsyncTask, Task
from pulp.server.dispatch.taskqueue import TaskQueue

# coordinator class ------------------------------------------------------------

class Coordinator(object):
    """
    Coordinator class that runs call requests in the task queue and detects and
    resolves conflicting operations on resources.
    @ivar task_queue: the task queue to run call requests in
    @type task_queue: L{TaskQueue} instance
    @ivar task_resource_collection: mongodb collection for task resources
    @type task_resource_collection: L{pymongo.Collection} instance
    @ivar task_wait_sleep_interval: sleep interval to use while polling a "synchronous" task
    @type task_wait_sleep_interval: float
    """

    def __init__(self, task_queue, task_wait_sleep_interval=0.5):
        assert isinstance(task_queue, TaskQueue)

        self.task_queue = task_queue
        self.task_resource_collection = TaskResource.get_collection()
        self.task_wait_sleep_interval = task_wait_sleep_interval

    # execution methods --------------------------------------------------------

    def execute_call(self, call_request):
        """
        Execute a call request in the tasking sub-system.
        This will run the task synchronously if no conflicts are detected,
        asynchronously if there are tasks that will postpone this one.
        @param call_request: call request to run
        @type  call_request: L{call.CallRequest} instance
        @return: call report pertaining to the running of the request call
        @rtype:  L{call.CallReport} instance
        """
        task = self._create_task(call_request)
        synchronous = None
        if isinstance(task, AsyncTask):
            synchronous = False
        self._run_task(task, synchronous)
        return copy.copy(task.call_report)

    def execute_call_synchronously(self, call_request, timeout=None):
        """
        Execute a call request in the tasking sub-system.
        This will run the task synchronously regardless of postponing conflicts.
        NOTE: this method cannot be used to execute asynchronous tasks.
        @param call_request: call request to run
        @type  call_request: L{call.CallRequest} instance
        @param timeout: maximum amount of time to wait for the task to start
        @type  timeout: None or datetime.timedelta
        @return: call report pertaining to the running of the request call
        @rtype:  L{call.CallReport} instance
        """
        assert isinstance(timeout, (datetime.timedelta, types.NoneType))
        task = self._create_task(call_request)
        if isinstance(task, AsyncTask):
            raise dispatch_exceptions.AsynchronousExecutionError(call_request)
        self._run_task(task, True, timeout)
        return copy.copy(task.call_report)

    def execute_call_asynchronously(self, call_request):
        """
        Execute a call request in the tasking sub-system.
        This will run the task asynchronously regardless of no postponing conflicts.
        @param call_request: call request to run
        @type  call_request: L{call.CallRequest} instance
        @return: call report pertaining to the running of the request call
        @rtype:  L{call.CallReport} instance
        """
        task = self._create_task(call_request)
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
        job_id = self._generate_job_id()
        call_report_list = []
        for call_request in call_request_list:
            task = self._create_task(call_request, job_id)
            self._run_task(task, False)
            call_report_list.append(copy.copy(task.call_report))
        return call_report_list

    # execution utilities ------------------------------------------------------

    def _create_task(self, call_request, job_id=None):
        """
        Create the task for the given call request.
        @param call_request: call request to encapsulate in a task
        @type  call_request: L{call.CallRequest} instance
        @param job_id: optional job id
        @type  job_id: None or str
        @return: task that encapsulates the call request
        @rtype:  L{Task} instance
        """
        if call_request.success_failure_callback_kwargs is None:
            task = Task(call_request)
        else:
            task = AsyncTask(call_request)
            task.set_success_failure_callback_kwargs(*call_request.success_failure_callback_kwargs)
        task.call_report.task_id = task.id
        task.call_report.job_id = job_id
        if call_request.progress_callback_kwarg is not None:
            task.set_progress_callback(call_request.progress_callback_kwarg)
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
        self.task_queue.lock()
        try:
            task.call_request.add_execution_hook(dispatch_constants.CALL_COMPLETE_EXECUTION_HOOK, coordinator_complete_callback)
            response, blocking, reasons, task_resources = self._find_conflicts(task.call_request.resources)
            task.call_report.response = response
            task.call_report.reason = reasons
            if response is dispatch_constants.CALL_REJECTED_RESPONSE:
                return
            task.blocking_tasks = blocking
            if task_resources:
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

    def _generate_job_id(self):
        """
        Generate a unique job id.
        @return: uuid string
        @rtype:  str
        """
        # NOTE this needs to utilize a central locking mechanism because on
        # Python < 2.5 the uuid package can generate non-unique ids if more than
        # one thread accesses it at a time
        self.task_queue.lock()
        try:
            job_id = str(uuid.uuid4())
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
        if not resources:
            return dispatch_constants.CALL_ACCEPTED_RESPONSE, set(), [], []

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

    def find_tasks(self, **criteria):
        """
        Find call reports that match the criteria given as key word arguments.

        Supported criteria:
         * task_id
         * job_id
         * state
         * call_name
         * class_name
         * args
         * kwargs
         * resources
         * tags
        """
        valid_criteria = set(('task_id', 'job_id', 'state', 'call_name',
                              'class_name', 'args', 'kwargs', 'resources', 'tags'))
        provided_criteria = set(criteria.keys())
        superfluous_criteria = provided_criteria - valid_criteria
        if superfluous_criteria:
            raise dispatch_exceptions.UnrecognizedSearchCriteria(*list(superfluous_criteria))
        tasks = []
        for task in self.task_queue.all_tasks():
            if task_matches_criteria(task, criteria):
                tasks.append(task)
        return tasks

    def find_call_reports(self, **criteria):
        """
        Find call reports that match the criteria given as key word arguments.

        Supported criteria:
         * task_id
         * job_id
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

    def cancel_call(self, task_id):
        """
        Cancel a call request using the task id.
        @param task_id: task id for call request to cancel
        @type  task_id: str
        @return: True if the task is being cancelled, False if not, or None if the task was not found
        @rtype:  bool or None
        """
        task = self.task_queue.get(task_id)
        if task is None:
            return None
        return self.task_queue.cancel(task)

    def cancel_multiple_calls(self, job_id):
        """
        Cancel multiple call requests using the job id.
        @param job_id: job id for multiple calls
        @type  job_id: str
        @return: dictionary of {task id: cancel return} for tasks associated with the job id
        @rtype:  dict
        """
        cancel_returns = {}
        for task in self.task_queue.all_tasks():
            if job_id != task.call_report.job_id:
                continue
            cancel_returns[task.id] = self.task_queue.cancel(task)
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
    if 'job_id' in criteria and criteria['job_id'] != task.call_report.job_id:
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

