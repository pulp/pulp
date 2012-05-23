# -*- coding: utf-8 -*-
#
# Copyright © 2011-2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from datetime import datetime, timedelta

from pulp.common import dateutils
from pulp.common.tags import resource_tag
from pulp.server.db.model.gc_base import Model
from pulp.server.dispatch import constants as dispatch_constants


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


class ScheduledCall(Model):
    """
    Serialized scheduled call request
    """

    collection_name = 'scheduled_calls'
    unique_indices = ()
    search_indices = ('serialized_call_request.tags', 'last_run', 'next_run')

    def __init__(self, call_request, schedule, failure_threshold=None, last_run=None, enabled=True):
        super(ScheduledCall, self).__init__()

        schedule_tag = resource_tag(dispatch_constants.RESOURCE_SCHEDULE_TYPE, str(self._id))
        call_request.tags.append(schedule_tag)
        interval, start, runs = dateutils.parse_iso8601_interval(schedule)
        now = datetime.utcnow()
        zero = timedelta(seconds=0)
        start = start and dateutils.to_naive_utc_datetime(start)

        self.serialized_call_request = call_request.serialize()
        self.schedule = schedule
        self.failure_threshold = failure_threshold
        self.consecutive_failures = 0
        self.first_run = start or now
        while interval > zero and self.first_run <= now:
            # try to schedule the first run in the future
            self.first_run += interval
        self.last_run = last_run and dateutils.to_naive_utc_datetime(last_run)
        self.next_run = None # will calculated and set by the scheduler
        self.remaining_runs = runs
        self.enabled = enabled


class ArchivedCall(Model):
    """
    Call history
    """

    collection_name = 'archived_calls'
    unique_indices = ()
    search_indices = ()

    def __init__(self, call_request, call_report):
        super(ArchivedCall, self).__init__()
        self.serialized_call_request = call_request.serialize()
        self.serialized_call_report = call_report.serialize()


class TaskResource(Model):
    """
    Information for an individual resource used by a task.
    """

    collection_name = 'task_resources'
    search_indices = ('task_id', 'resource_type', 'resource_id')

    def __init__(self, task_id, resource_type, resource_id, operation):
        super(TaskResource, self).__init__()
        self.task_id = task_id
        self.resource_type = resource_type
        self.resource_id  = resource_id
        self.operation = operation

