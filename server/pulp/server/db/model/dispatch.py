# -*- coding: utf-8 -*-
#
# Copyright © 2011-2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from datetime import datetime

from pulp.common import dateutils
from pulp.common.tags import resource_tag
from pulp.server.db.model.base import Model
from pulp.server.dispatch import constants as dispatch_constants


class CallResource(Model):
    """
    Information for an individual resource used by a call request.
    """

    collection_name = 'call_resources'
    search_indices = ('call_request_id', 'resource_type', 'resource_id')

    def __init__(self, call_request_id, resource_type, resource_id, operation):
        super(CallResource, self).__init__()
        self.call_request_id = call_request_id
        self.resource_type = resource_type
        self.resource_id  = resource_id
        self.operation = operation


class QueuedCall(Model):
    """
    Serialized queued call request
    """

    collection_name = 'queued_calls'
    unique_indices = ()

    def __init__(self, call_request):
        super(QueuedCall, self).__init__()
        self.serialized_call_request = call_request.serialize()
        self.timestamp = datetime.now()


class QueuedCallGroup(Model):
    """
    """

    collection_name = 'queued_call_groups'
    unique_indices = ('group_id',)

    def __init__(self, call_request_group_id, call_request_ids):
        super(QueuedCallGroup, self).__init__()

        self.call_request_group_id = call_request_group_id
        self.call_request_ids = call_request_ids

        self.total_calls = len(call_request_ids)
        self.completed_calls = 0


class ScheduledCall(Model):
    """
    Serialized scheduled call request
    """

    collection_name = 'scheduled_calls'
    unique_indices = ()
    search_indices = ('serialized_call_request.tags', 'last_run', 'next_run')

    def __init__(self, call_request, schedule, failure_threshold=None, last_run=None, enabled=True):
        super(ScheduledCall, self).__init__()

        # add custom scheduled call tag to call request
        schedule_tag = resource_tag(dispatch_constants.RESOURCE_SCHEDULE_TYPE, str(self._id))
        call_request.tags.append(schedule_tag)

        self.serialized_call_request = call_request.serialize()

        self.schedule = schedule
        self.enabled = enabled

        self.failure_threshold = failure_threshold
        self.consecutive_failures = 0

        # scheduling fields
        self.first_run = None # will be calculated and set by the scheduler
        self.last_run = last_run and dateutils.to_naive_utc_datetime(last_run)
        self.next_run = None # will be calculated and set by the scheduler
        self.remaining_runs = dateutils.parse_iso8601_interval(schedule)[2]

        # run-time call group metadata for tracking success or failure
        self.call_count = 0
        self.call_exit_states = []


class ArchivedCall(Model):
    """
    Call history
    """

    collection_name = 'archived_calls'
    unique_indices = ()
    search_indices = ('serialized_call_report.call_request_id',
                      'serialized_call_report.call_request_group_id')

    def __init__(self, call_request, call_report):
        super(ArchivedCall, self).__init__()
        self.timestamp = dateutils.now_utc_timestamp()
        self.call_request_string = str(call_request)
        self.serialized_call_report = call_report.serialize()


class TaskStatus(Model):
    """
    Represents current state of a task.

    :ivar task_id:     identity of the task this status corresponds to
    :type task_id:     basestring
    :ivar tags:        custom tags on the task
    :type tags:        list
    :ivar state:       state of callable in its lifecycle
    :type state:       basestring
    :ivar result:      return value of the callable, if any
    :type result:      any
    :ivar traceback:   string representation of the traceback from callable, if any
    :type traceback:   basestring
    :ivar start_time:  time the task started executing
    :type start_time:  datetime.datetime
    :ivar finish_time: time the task completed
    :type finish_time: datetime.datetime
    :ivar queue:       The queue that the Task was queued in
    :type queue:       basestring
    """

    collection_name = 'task_status'
    unique_indices = ('task_id',)
    search_indices = ('task_id', 'tags', 'state')

    def __init__(self, task_id, queue, tags=None, state=None):
        super(TaskStatus, self).__init__()

        self.task_id = task_id
        self.queue = queue
        self.tags = tags or []
        self.state = state
        self.result = None
        self.traceback = None
        self.start_time = None
        self.finish_time = None
