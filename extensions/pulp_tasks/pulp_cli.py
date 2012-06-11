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

from gettext import gettext as _
import sys

import pulp.common.tags as tag_utils
from pulp.client.extensions.extensions import PulpCliSection
from pulp.client.extensions.exceptions import PulpServerException

# -- constants ----------------------------------------------------------------

# Guidance for render_document_list on how to display task info
TASK_DOC_ORDER = ['operations', 'resources', 'state', 'start_time', 'finish_time', 'result', 'task_id']

# -- framework hooks ----------------------------------------------------------

def initialize(context):

    # Add root level section for all tasks in Pulp
    all_tasks_section = AllTasksSection(context, 'tasks', _('list and cancel tasks running in the Pulp server'))
    context.cli.add_section(all_tasks_section)

    # Add repo level section for only repo tasks
    repo_tasks_section = RepoTasksSection(context, 'tasks', _('list and cancel tasks related to a specific repository'))
    repo_section = context.cli.find_section('repo')
    repo_section.add_subsection(repo_tasks_section)

# -- sections -----------------------------------------------------------------

class BaseTasksSection(PulpCliSection):
    """
    Base class for handling tasks in the Pulp server. This should be subclassed
    to provide consistent functionality for a subset of tasks.
    """

    def __init__(self, context, name, description):
        PulpCliSection.__init__(self, name, description)
        self.context = context

        # Store the command instances as instance variables so the subclasses
        # can manipulate them if necessary

        self.list_command = self.create_command('list', _('lists tasks queued or running in the server'), self.list)

        self.cancel_command = self.create_command('cancel', _('cancel one or more tasks'), self.cancel)
        self.cancel_command.create_option('--task-id', _('identifies the task to cancel'), required=True)

        self.details_command = self.create_command('details', _('displays more detailed information about a specific task'), self.details)
        self.details_command.create_option('--task-id', _('identifies the task'), required=True)

    def list(self, **kwargs):
        """
        Displays a list of tasks. The list of tasks is driven by the
        retrieve_tasks method which should be overridden to provide the
        correct behavior.
        """

        self.context.prompt.render_title('Tasks')

        response = self.retrieve_tasks(**kwargs)
        task_objects = response.response_body

        # Easy out clause
        if len(task_objects) is 0:
            self.context.prompt.render_paragraph('No tasks found')
            return

        # Parse each task object into a document to be displayed using the
        # prompt utilities
        task_documents = []
        for task in response.response_body:

            # Interpret task values
            state, start_time, finish_time = self.parse_state(task)
            actions, resources = self.parse_tags(task)
            result = self.parse_result(task)

            task_doc = {
                'operations' : ', '.join(actions),
                'resources' : ', '.join(resources),
                'task_id' : task.task_id,
                'state' : state,
                'start_time' : start_time,
                'finish_time' : finish_time,
                'result' : result,
            }
            task_documents.append(task_doc)

        self.context.prompt.render_document_list(task_documents, order=TASK_DOC_ORDER)

    def details(self, **kwargs):
        """
        Displays detailed information about a single task. The task ID must
        be in kwargs under "task-id".
        """

        self.context.prompt.render_title('Task Details')

        task_id = kwargs['task-id']
        response = self.context.server.tasks.get_task(task_id)
        task = response.response_body

        # Interpret task values
        state, start_time, finish_time = self.parse_state(task)
        actions, resources = self.parse_tags(task)
        result = self.parse_result(task)

        # Assemble document to be displayed
        task_doc = {
            'operations' : ', '.join(actions),
            'resources' : ', '.join(resources),
            'task_id' : task.task_id,
            'state' : state,
            'start_time' : start_time,
            'finish_time' : finish_time,
            'result' : result,
            'progress' : task.progress,
        }

        if task.exception:
            task_doc['exception'] = task.exception

        if task.traceback:
            task_doc['traceback'] = task.traceback

        self.context.prompt.render_document(task_doc, order=TASK_DOC_ORDER)

    def cancel(self, **kwargs):
        """
        Attempts to cancel a task. Only unstarted tasks and those that support
        cancellation (sync, publish) can be canceled. If a task does not support
        cancelling, a not implemented error (501) will be raised from the server.
        We should handle that gracefully to explain to the user what happend.
        Otherwise, all other errors should bubble up to the exception middleware
        as usual.
        """

        task_id = kwargs['task-id']

        try:
            self.context.server.tasks.cancel_task(task_id)
        except PulpServerException, e:

            # A 501 has a bit of a special meaning here that's not used in the
            # exception middleware, so handle it here.
            if e.http_status == 501:
                msg = _('The requested task does not support cancellation.')
                self.context.prompt.render_failure_message(msg)
                return
            else:
                raise e, None, sys.exc_info()[2]

    # -- rendering utilities --------------------------------------------------

    def parse_state(self, task):
        """
        Uses the state of the task to return user-friendly descriptions of the
        state and task timing values.

        @param task: object representation of the task
        @type  task: Task

        @return: tuple of state, start time, and finish time
        @rtype: (str, str, str)
        """
        state = _('Unknown')
        start_time = _('Unstarted')
        finish_time = _('Incomplete')

        if task.is_rejected():
            state = _('Rejected')
        elif task.is_postponed() or task.is_waiting():
            state = _('Waiting')
        elif task.is_running():
            state = _('Running')
            start_time = task.start_time
        elif task.is_completed():
            finish_time = task.finish_time
            if task.was_successful():
                state = _('Successful')
            elif task.was_failure():
                state = _('Failed')
            elif task.was_cancelled():
                state = _('Cancelled')

        return state, start_time, finish_time

    def parse_tags(self, task):
        """
        Uses the tags entry in the task to render a user-friendly display of
        the actions and resources involved in the task.

        @param task: object representation of the task
        @type  task: Task

        @return: tuple of list of actions and list of resources involved
        @rtype:  ([], [])
        """

        actions = []
        resources = []

        for t in task.tags:
            if tag_utils.is_resource_tag(t):
                resource_type, resource_id = tag_utils.parse_resource_tag(t)
                resources.append('%s (%s)' % (resource_id, resource_type))
            else:
                tag_value = tag_utils.parse_value(t)
                actions.append(tag_value)

        return actions, resources

    def parse_result(self, task):
        """
        Converts the result of the task into a user-friendly explanation.

        @param task: object representation of the task
        @type  task: Task

        @return: tuple of list of actions and list of resources involved
        @rtype:  ([], [])
        """
        return task.result or _('Incomplete')

# -- override below -------------------------------------------------------

    def retrieve_tasks(self):
        """
        Override this with the specific call to the server to retrieve just
        the desired tasks.

        @return: response from the server
        """
        raise NotImplemented()

class AllTasksSection(BaseTasksSection):
    def retrieve_tasks(self, **kwargs):
        response = self.context.server.tasks.get_all_tasks()
        return response

class RepoTasksSection(BaseTasksSection):
    def __init__(self, context, name, description):
        BaseTasksSection.__init__(self, context, name, description)

        self.list_command.create_option('--repo-id', _('identifies the repository to display'), required=True)

    def retrieve_tasks(self, **kwargs):
        repo_id = kwargs['repo-id']
        response = self.context.server.tasks.get_repo_tasks(repo_id)
        return response
