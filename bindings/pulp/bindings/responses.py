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


RESPONSE_ACCEPTED = 'accepted'
RESPONSE_POSTPONED = 'postponed'
RESPONSE_REJECTED = 'rejected'

STATE_ACCEPTED = 'accepted'
STATE_RUNNING = 'running'
STATE_WAITING = 'waiting'
STATE_FINISHED = 'finished'
STATE_ERROR = 'error'
STATE_CANCELED = 'canceled'
STATE_SKIPPED = 'skipped'

COMPLETED_STATES = (STATE_FINISHED, STATE_ERROR, STATE_CANCELED, STATE_SKIPPED)


class Response(object):
    """
    Contains the data received from the server on a successful request.
    """
    def __init__(self, response_code, response_body):
        self.response_code = response_code
        self.response_body = response_body

    def __str__(self):
        return _("Response: code [%(c)s] body [%(b)s]") % {'c' : self.response_code, 'b' : self.response_body}

    def is_async(self):
        """
        Returns if the response indicated an asynchronous task has been queued
        on the server. If this returns true, the response_body will be a Task.
        Otherwise, the response body will be a Document.

        @return: true if the request did not immediately execute and complete
                 but rather was queued to be run asynchronously
        @rtype:  bool
        """
        return isinstance(self.response_body, Task)


class Task(object):
    """
    Contains the data received from a call to the server that describes an
    asynchronous call queued or running on the server.

    This class provides a number of utility methods for interpreting the state
    of the task which should be used whenever possible instead of manually
    interpreting the structure of the data within.

    Below is a sample task dictionary that can be copied for unit tests that
    need to simulate a task response:

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
        "progress_report": {},
    }
    """

    def __init__(self, response_body):
        """
        Initialize the Task based on the data returned from Pulp's task API.

        :param response_body: The de-serialized response from Pulp's task API
        :type  response_body: dict
        """
        # Tasking identity information
        if '_href' in response_body:
            self.href = response_body['_href']
        else:
            self.href = None

        self.task_id = response_body.get('task_id')
        self.tags = response_body.get('tags', [])

        self.start_time = response_body.get('start_time')
        self.finish_time = response_body.get('finish_time')

        # Related to the callable being executed
        self.state = response_body.get('state')
        self.progress_report = response_body.get('progress_report')
        self.result = response_body.get('result')
        self.exception = response_body.get('exception')
        self.traceback = response_body.get('traceback')
        self.error = response_body.get('error')
        self.spawned_tasks = []
        spawned_tasks = response_body.get('spawned_tasks')
        if spawned_tasks:
            for task in spawned_tasks:
                self.spawned_tasks.append(Task(task))

    def is_waiting(self):
        """
        Indicates if the task has been accepted but has not yet been able to
        run. This may be due to the task being blocked by another task or
        because the server is busy with other items.

        :rtype: bool
        """
        return self.state == STATE_WAITING

    def is_running(self):
        """
        Indicates if the task is in the process of running on the server.

        :rtype: bool
        """
        return self.state == STATE_RUNNING

    def was_accepted(self):
        """
        Indicates if the task was accepted by the agent.

        :rtype: bool
        """
        return self.state == STATE_ACCEPTED

    def is_completed(self):
        """
        Indicates if the task has finished running and will not begin again,
        regardless of the result (error, success, or cancelled).

        :rtype: bool
        """
        return self.state in COMPLETED_STATES

    def was_successful(self):
        """
        Indicates if a task finished successfully. If the task is not finished,
        this call returns False.

        :rtype: bool
        """
        return self.state == STATE_FINISHED

    def was_failure(self):
        """
        Indicates if a task finished with an error. If the task is not finished,
        this call returns False.

        :rtype: bool
        """
        return self.state == STATE_ERROR

    def was_skipped(self):
        """
        Indicates if a task was skipped. If the task is not finished, this call
        returns False

        :rtype: bool
        """
        return self.state == STATE_SKIPPED

    def was_cancelled(self):
        """
        Indicates if a task was cancelled.

        :rtype: bool
        """
        return self.state == STATE_CANCELED

    def __str__(self):
        """
        Return a string representation of this Task.

        :return: String representation of self
        :rtype:  unicode
        """
        return _(u'Task: %(id)s State: %(state)s') % {'id': self.task_id, 'state': self.state}


class BlockingReason(object):
    """
    Represents a single reason a task was postponed or blocked.
    """
    def __init__(self, resource_id, resource_type, operation):
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.operation = operation

    def __str__(self):
        subs = {'i' : self.resource_id,
                't' : self.resource_type,
                'o' : self.operation,
        }
        return _('BlockingReason: id [%(i)s] type [%(t)s] operation [%(o)s]') % subs
