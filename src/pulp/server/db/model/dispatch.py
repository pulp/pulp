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


class ScheduledCall(Model):
    """
    Serialzed scheduled call request
    """

    collection_name = 'scheduled_calls'
    unique_indices = ()
    search_indices = ('serialized_call_request.tags', 'last_run', 'next_run')

    def __init__(self, call_request, schedule, last_run=None, enabled=True):
        super(ScheduledCall, self).__init__()

        call_request.tags.append(self._id)

        self.serialized_call_request = call_request.serialize()
        self.schedule = schedule
        self.last_run = dateutils.to_naive_utc_datetime(last_run)
        self.enabled = enabled

        interval, start_date, runs = dateutils.parse_iso8601_interval(schedule)
        if start_date is None:
            start_date = datetime.utcnow()

        self.interval = interval
        self.start_date = dateutils.to_naive_utc_datetime(start_date)
        self.runs = runs

        self.next_run = None # will calculated and set by the scheduler
