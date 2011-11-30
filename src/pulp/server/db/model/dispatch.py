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

from pulp.common import dateutils
from pulp.server.db.model.base import Model


class QueuedCall(Model):

    collection_name = 'queued_calls'
    unique_indicies = ()


class ScheduledCall(Model):

    collection_name = 'scheduled_calls'
    unique_indices = ()
    search_indices = ('serialized_call_request.tags', 'last_run', 'next_run')

    def __init__(self, call_request, schedule, last_run=None):
        self.serialized_call_request = call_request.serialize()
        interval, start_date, runs = dateutils.parse_iso8601_interval(schedule)
        self.interval = interval
        self.runs = runs
        self.last_run = last_run or start_date
        # can't store tzinfo, so normalize to utc and then get rid of tzinfo
        self.last_run = self.last_run.astimezone(dateutils.utc_tz())
        self.last_run = self.last_run.replaze(tzinfo=None)
        # next run will be calculated and assigned by the scheduler
        self.next_run = None
