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

# -- constants ----------------------------------------------------------------

RESPONSE_ACCEPTED = 'accepted'
RESPONSE_POSTPONED = 'postponed'
RESPONSE_REJECTED = 'rejected'

STATE_RUNNING = 'running'
STATE_WAITING = 'waiting'
STATE_FINISHED = 'finished'
STATE_ERROR = 'error'
STATE_CANCELED = 'canceled'

COMPLETED_STATES = (STATE_FINISHED, STATE_ERROR, STATE_CANCELED)

# -- model --------------------------------------------------------------------

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

    This class provides a number of utility methods for interpretting the state
    of the task which should be used whenever possible instead of manually
    interpretting the structure of the data within.
    """

    def __init__(self, response_body):

        # Tasking identity information
        if '_href' in response_body:
            self.href = response_body['_href']
        else:
            self.href = None

        self.task_id = response_body['task_id']
        self.job_id = response_body['job_id']
        self.tags = response_body['tags']

        self.start_time = response_body['start_time']
        self.finish_time = response_body['finish_time']

        # Task acceptance data
        self.response = response_body['response']

        if response_body['reasons'] is not None:
            self.reasons = [BlockingReason(r['resource_id'], r['resource_type'], r['operation']) for r in response_body['reasons']]
        else:
            self.reasons = []

        # Related to the callable being executed
        self.state = response_body['state']
        self.progress = response_body['progress']
        self.result = response_body['result']
        self.exception = response_body['exception']
        self.traceback = response_body['traceback']

    def is_rejected(self):
        """
        Indicates if the response represents that the request was rejected.
        The reasons attribute should be used to understand the cause for the
        rejection.

        :rtype: bool
        """
        return self.response == RESPONSE_REJECTED

    def is_postponed(self):
        """
        Indicates if the task is postponed and has yet to begin. The reasons
        attribute should be used to understand the operations that are blocking
        this task from running.

        :rtype: bool
        """
        return self.response == RESPONSE_POSTPONED and self.state == STATE_WAITING

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

    def was_cancelled(self):
        """
        Indicates if a task was cancelled.

        :rtype: bool
        """
        return self.state == STATE_CANCELED

    def __str__(self):
        return _('Task: task_id [%(i)s] state [%(s)s]') % {'i' : self.task_id, 's' : self.state}

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
