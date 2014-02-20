# -*- coding: utf-8 -*-
# Copyright (c) 2013 Red Hat, Inc.
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
Contains functionality to simulate returning tasks that change state at each invocation. This
should be used for any command that uses asynchronous REST APIs to reduce the need for each
test to create the proper task format.

A TaskSimulator instance is configured with the task information being simulated by
the server. For each task, an ordered list of states can be supplied. Each request to
the server for retrieving the task removes the appropriate state from the configuration;
simulations should be recreated between tests as the running of the task retrieval
will destroy the test data.

The install method on the object can be used to insert it into the correct location in the
bindings object.
"""

import copy

from pulp.bindings import responses


TASK_TEMPLATE = {
    "exception": None,
    "task_id": 'default-id',
    "tags": [],
    "start_time": None,
    "traceback": None,
    "state": None,
    "finish_time": None,
    "schedule_id": None,
    "result": None,
    "progress": {},
    "response": None,
}


class TaskSimulator(object):
    """
    Used to simulate the progression of tasks across states. See the module-level docstrings
    for more information on usage.
    """

    def __init__(self):
        # Mapping of task ID to ordered list of Task instances. The Task instances are ordered
        # by newest added first.
        self.tasks_by_id = {}
        self.ordered_task_ids = []  # task IDs ordered in the way they were added

    def install(self, bindings):
        """
        Installs this simulator into the bindings instance provided in the client context to
        the command being tested. If using the PulpClientTests base class, this is simply
        self.bindings.

        :param bindings: bindings instance to install this simulator instance into
        :type  bindings: pulp.bindings.bindings.Bindings
        """
        bindings.tasks = self

    def add_task_state(self, task_id, state, progress_report=None, spawned_tasks=None):
        """
        Adds a new state entry for the given task ID. If the there are currently no states listed
        for the given ID, this call will cause the new task ID to be created and thus returned from
        the get_all_tasks call. The order in which these task IDs are created will be tracked and
        honored in get_all_tasks.

        If doing some sort of polling operation, you'll likely need to add one of the completed states
        once you've added all of the desired waiting/running states. This simulator will continue
        to pop off the next task state for this task_id each time get_task is called, so if
        your code is polling until completion, don't be surprised to find some form of index out of bounds
        error crop up.
        """
        new_task_dict = copy.deepcopy(TASK_TEMPLATE)
        new_task_dict['task_id'] = task_id
        new_task_dict['state'] = state
        new_task_dict['progress_report'] = progress_report

        new_task = responses.Task(new_task_dict)

        if isinstance(spawned_tasks, list):
            new_task.spawned_tasks = copy.copy(spawned_tasks)

        task_list_for_id = self.tasks_by_id.setdefault(task_id, [])
        # reverse order because popping from the end is more efficient and it will make jconnor happy
        task_list_for_id.insert(0, new_task)

        if task_id not in self.ordered_task_ids:
            self.ordered_task_ids.append(task_id)

        return new_task

    def add_task_states(self, task_id, state_list):
        """
        Shortcut for adding a series of states. The response will be ACCEPTED in all cases.

        :param task_id: task whose state list is being updated
        :type  task_id: str
        :param state_list: list of state values; should be codes from the pulp.bindings.responses module
        :type  state_list: list of str

        :return: list of created tasks corresponding to the same order of state_list
        """

        tasks = [self.add_task_state(task_id, s) for s in state_list]
        return tasks

    # -- task bindings api ----------------------------------------------------------------------------------

    def get_task(self, task_id):
        """
        Returns the next state for the given task.

        :return: response object as if the bindings had contacted the server
        :rtype:  pulp.bindings.response.Response

        :raises ValueError: if no states are defined for the given task ID
        """
        if task_id not in self.tasks_by_id:
            raise ValueError('No task states configured for task ID [%s]' % task_id)

        # Wrap the task in a response to simulate what comes out of the bindings
        task = self.tasks_by_id[task_id].pop()
        response = responses.Response('200', task)

        return response


    def get_all_tasks(self, tags=()):
        """
        Returns the next state for all tasks that match the given tags, if any. The index
        counters will be incremented such that on the next call to get_task, the state
        following what is returned from this call will be returned.

        This implementation currently does not use the tags parameter but should be
        enhanced to do so in the future.

        :return: response object as if the bindings had contacted the server
        :rtype:  pulp.bindings.response.Response
        """

        task_list = []
        for task_id in self.ordered_task_ids:
            next_task = self.tasks_by_id[task_id].pop()
            task_list.append(next_task)

        # Package the task list into the response object like the bindings would
        response = responses.Response('200', task_list)

        return response


def create_fake_task_response():
    """
    Returns a Response object that can be used as a mock return from a bindings call
    that is expected to return a task. The values for the task will be the same as
    those found in TASK_TEMPLATE.

    :return: response object with the parsed Task object in its response_body
    :rtype:  Response
    """
    task = responses.Task(TASK_TEMPLATE)
    response = responses.Response('202', task)
    return response
