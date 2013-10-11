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

import calendar
from datetime import datetime
import logging
import pickle
import time

from bson import ObjectId
from celery import current_app, beat, schedules
from celery.beat import ScheduleEntry
from celery.utils.timeutils import timedelta_seconds

from pulp.common import dateutils
from pulp.common.tags import resource_tag
from pulp.server.db.model.base import Model
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.webservices.serialization.db import scrub_mongo_fields


logger = logging.getLogger(__name__)


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


class OldScheduledCall(Model):
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


class ScheduledCall(Model):
    """
    Serialized scheduled call request
    """

    collection_name = 'scheduled_calls'
    unique_indices = ()
    search_indices = ('tags', 'last_run', 'last_updated')

    def __init__(self, iso_schedule, task, total_run_count, next_run,
                 schedule, args, kwargs, principal, last_updated,
                 consecutive_failures=0, enabled=True, failure_threshold=None,
                 last_run_at=None, first_run=None, remaining_runs=None, id=None,
                 tag=None, name=None):
        """
        :type  schedule_entry:  celery.beat.ScheduleEntry

        """
        super(ScheduledCall, self).__init__()

        self.consecutive_failures = consecutive_failures
        self.enabled = enabled
        self.failure_threshold = failure_threshold
        self.id = id
        self.iso_schedule = iso_schedule
        self.last_run_at = last_run_at
        self.last_updated = last_updated
        self.name = id
        self.next_run = next_run
        self.options = {}
        self.task = task
        self.total_run_count = total_run_count

        for key in ('schedule', 'args', 'kwargs', 'principal'):
            value = locals()[key]
            if isinstance(value, basestring):
                setattr(self, key, value)
            else:
                setattr(self, key, pickle.dumps(value))

        if first_run is None:
            self.first_run = dateutils.format_iso8601_datetime(
                dateutils.parse_iso8601_interval(iso_schedule)[1])
        elif isinstance(first_run, basestring):
            self.first_run = dateutils.parse_iso8601_datetime(first_run)
        else:
            self.first_run = first_run
        if remaining_runs is None:
            self.remaining_runs = dateutils.parse_iso8601_interval(iso_schedule)[2]
        else:
            self.remaining_runs = remaining_runs

        self.tag = tag or resource_tag(dispatch_constants.RESOURCE_SCHEDULE_TYPE, str(self._id))

    @classmethod
    def from_db(cls, call):
        """
        :rtype:     pulp.server.db.model.dispatch.ScheduledCall
        """
        call = scrub_mongo_fields(call)
        call.pop('_id', None)
        call.pop('_ns', None)
        return cls(**call)

    def as_schedule_entry(self):
        """
        :return:    a ScheduleEntry instance based on this object
        :rtype:     celery.beat.ScheduleEntry
        """
        last_run = dateutils.parse_iso8601_datetime(self.last_run_at)
        return ScheduleEntry(self.name, self.task, last_run, self.total_run_count,
                             pickle.loads(self.schedule), pickle.loads(self.args),
                             pickle.loads(self.kwargs), self.options,
                             self.relative, scheduled_call=self)

    @staticmethod
    def explode_schedule_entry(entry):
        """
        :param entry:
        :type  entry:   celery.beat.ScheduleEntry

        :return:    dict of data from a ScheduleEntry as it should be represented
                    to pass into the constructor of this class
        :rtype:     dict
        """
        schedule_keys = ('name', 'task', 'last_run_at', 'total_run_count',
                         'schedule', 'args', 'kwargs', 'app')
        return dict((k, getattr(entry, k)) for k in schedule_keys)

    def save(self):
        """
        Saves the current instance to the database
        """
        to_save = {
            'args': self.args,
            'consecutive_failures': self.consecutive_failures,
            'enabled': self.enabled,
            'failure_threshold': self.failure_threshold,
            'first_run': self.first_run,
            'id': self.id,
            'kwargs': self.kwargs,
            'iso_schedule': self.iso_schedule,
            'last_run_at': self.last_run_at,
            'last_updated': self.last_updated,
            'next_run': self.next_run,
            'principal': self.principal,
            'remaining_runs': self.remaining_runs,
            'schedule': self.schedule,
            'task': self.task,
            'total_run_count': self.total_run_count,
        }

        self.get_collection().update({'_id': ObjectId(self.id)}, to_save)


class ScheduleEntry(beat.ScheduleEntry):
    def __init__(self, *args, **kwargs):
        """
        :param scheduled_call:  the scheduled call that produced this instance
        :type  scheduled_call:  pulp.server.db.model.dispatch.ScheduledCall
        """
        self._scheduled_call = kwargs.pop('scheduled_call')
        super(ScheduleEntry, self).__init__(*args, **kwargs)

    def _next_instance(self, last_run_at=None):
        now_s, first_run_s, since_first_s, run_every_s, expected_runs,\
                last_scheduled_run_s = self._calculate_times()

        self._scheduled_call.last_run_at = dateutils.format_iso8601_utc_timestamp(time.time())
        self._scheduled_call.next_run = dateutils.format_iso8601_utc_timestamp(last_scheduled_run_s + run_every_s)
        self._scheduled_call.total_run_count += 1
        self._scheduled_call.save()
        return self._scheduled_call.as_schedule_entry()

    __next__ = next = _next_instance

    def _calculate_times(self):
        now_s = time.time()
        first_run_s = calendar.timegm(self._scheduled_call.first_run.utctimetuple())
        since_first_s = now_s - first_run_s
        run_every_s = timedelta_seconds(self.schedule.run_every)
        expected_runs = int(since_first_s/run_every_s)
        last_scheduled_run_s = first_run_s + expected_runs * run_every_s

        return now_s, first_run_s, since_first_s, run_every_s, expected_runs, last_scheduled_run_s


    def is_due(self):
        now_s, first_run_s, since_first_s, run_every_s, expected_runs, \
                last_scheduled_run_s = self._calculate_times()

        # seconds remaining until the next time this should run, not counting
        # whether it gets run now or not
        remaining_s = last_scheduled_run_s + run_every_s - now_s

        # if the first run is in the future, don't run it now
        if since_first_s < 0:
            logger.debug('not running task %s: first run is in the future' % self.name)
            return False, -since_first_s
        # if it hasn't run before, run it now
        if not (self.total_run_count and self.last_run_at):
            logger.debug('running task %s: it has never run before' % self.name)
            return True, remaining_s

        last_run_s = calendar.timegm(self.last_run_at.utctimetuple())

        # is this hasn't run since the most recent scheduled run, then run now
        if last_run_s < last_scheduled_run_s:
            logger.debug('running task %s: it has been %d seconds since last run' % (
                         self.name, now_s - last_run_s))
            return True, remaining_s
        else:
            logger.debug('not running task %s: %d seconds remaining' % (
                         self.name, remaining_s))
            return False, remaining_s


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
