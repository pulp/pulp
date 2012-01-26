# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
from pulp.server.db.model.base import Model


class QueuedCall(Model):
    """
    Serialized queued call request
    """

    collection_name = 'queued_calls'
    unique_indices = ()

    def __init__(self, call_request):
        super(QueuedCall, self).__init__()
        self.serialized_call_request = call_request.serialize()


class ScheduledCall(Model):
    """
    Serialized scheduled call request
    """

    collection_name = 'scheduled_calls'
    unique_indices = ()
    search_indices = ('serialized_call_request.tags', 'last_run', 'next_run')

    def __init__(self, call_request, schedule, failure_threshold=None, last_run=None, enabled=True):
        super(ScheduledCall, self).__init__()

        call_request.tags.append(self._id)

        self.serialized_call_request = call_request.serialize()
        self.schedule = schedule
        self.failure_threshold = failure_threshold
        self.consecutive_failures = 0
        self.last_run = last_run and dateutils.to_naive_utc_datetime(last_run)
        self.enabled = enabled

        interval, start_date, runs = dateutils.parse_iso8601_interval(schedule)
        start_date = start_date or datetime.now()

        self.interval_in_seconds = interval.total_seconds()
        self.start_date = dateutils.to_naive_utc_datetime(start_date)
        self.remaining_runs = runs

        self.next_run = None # will calculated and set by the scheduler


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

