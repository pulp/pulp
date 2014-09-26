# -*- coding: utf-8 -*-
#
# Copyright © 2011-2014 Red Hat, Inc.
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
import calendar
import copy
import logging
import pickle
import time

from bson import ObjectId
from celery import beat
from celery.schedules import schedule as CelerySchedule
from celery.utils.timeutils import timedelta_seconds
import isodate

from pulp.common import dateutils
from pulp.server.async.celery_instance import celery as app
from pulp.server.db.model.base import Model
from pulp.server.db.model.reaper_base import ReaperMixin
from pulp.server.managers import factory


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
        self.resource_id = resource_id
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
    USER_UPDATE_FIELDS = frozenset(['iso_schedule', 'args', 'kwargs', 'enabled',
                                    'failure_threshold'])

    collection_name = 'scheduled_calls'
    unique_indices = ()
    search_indices = ('resource', 'last_updated')

    def __init__(self, iso_schedule, task, total_run_count=0, next_run=None,
                 schedule=None, args=None, kwargs=None, principal=None, last_updated=None,
                 consecutive_failures=0, enabled=True, failure_threshold=None,
                 last_run_at=None, first_run=None, remaining_runs=None, id=None,
                 tags=None, name=None, options=None, resource=None):
        """
        :param iso_schedule:        string representing the schedule in ISO8601 format
        :type  iso_schedule:        basestring
        :param task:                the task that should be run on a schedule. This
                                    can be an instance of a celery task or the name
                                    of the task, as taken from a task's "name" attribute
        :type  task:                basestring or celery.Task
        :param total_run_count:     total number of times this schedule has run
        :type  total_run_count:     int
        :param next_run:            ignored, because it is always re-calculated at instantiation
        :param schedule:            pickled instance of celery.schedules.schedule,
                                    representing the schedule that should be run.
                                    This is optional.
        :type  schedule:            basestring or None
        :param args:                list of arguments that should be passed to the
                                    task's apply_async function as its "args" argument
        :type  args:                list
        :param kwargs:              dict of keyword arguments that should be passed to the task's
                                    apply_async function as its "kwargs" argument
        :type  kwargs:              dict
        :param principal:           pickled instance of pulp.server.db.model.auth.User
                                    representing the pulp user who the task
                                    should be run as. This is optional.
        :type  principal:           basestring or None
        :param last_updated:        timestamp for the last time this schedule was updated in the
                                    database as seconds since the epoch
        :type  last_updated:        float
        :param consecutive_failures:    number of times this task has failed consecutively. This
                                        gets reset to zero if the task succeeds.
        :type  consecutive_failures:    int
        :param enabled:             boolean indicating whether this schedule should be actively run
                                    by the scheduler. If False, the schedule will be ignored.
        :type  enabled:             bool
        :param failure_threshold:   number of consecutive failures after which this task should be
                                    automatically disabled. Because these tasks run asynchronously,
                                    they may finish in a different order than they were queued in.
                                    Thus, it is possible that n consecutive failures will be
                                    reported by jobs that were not queued consecutively. So do not
                                    depend on the queuing order when using this feature. If this
                                    value is 0, no automatic disabling will occur.
        :type  failure_threshold:   int
        :param last_run_at:         ISO8601 string representing when this schedule last ran.
        :type  last_run_at:         basestring
        :param first_run:           ISO8601 string or datetime instance (in UTC timezone)
                                    representing when this schedule should run or should have been
                                    run for the first time. If the schedule has a specified date and
                                    time to start, this will be that value. If not, the value from
                                    the first time the schedule was actually run will be used.
        :type  first_run:           basestring or datetime.datetime or NoneType
        :param remaining_runs:      number of runs remaining until this schedule will be
                                    automatically disabled.
        :type  remaining_runs:      int or NoneType
        :param id:                  unique ID used by mongodb to identify this schedule
        :type  id:                  basestring
        :param tags:                ignored, but allowed to exist as historical
                                    data for now
        :param name:                ignored, because the "id" value is used for this now. The value
                                    is here for backward compatibility.
        :param options:             dictionary that should be passed to the apply_async function as
                                    its "options" argument.
        :type  options:             dict
        :param resource:            optional string indicating a unique resource that should be used
                                    to find this schedule. For example, to find all schedules for a
                                    given repository, a resource string will be derived for that
                                    repo, and this collection will be searched for that resource
                                    string.
        :type  resource:            basestring
        """
        if id is None:
            # this creates self._id and self.id
            super(ScheduledCall, self).__init__()
            self._new = True
        else:
            self.id = id
            self._id = ObjectId(id)
            self._new = False

        if hasattr(task, 'name'):
            task = task.name

        # generate this if it wasn't passed in
        if schedule is None:
            interval, start_time, occurrences = dateutils.parse_iso8601_interval(iso_schedule)
            schedule = pickle.dumps(CelerySchedule(interval))

        # generate this if it wasn't passed in
        principal = principal or factory.principal_manager().get_principal()

        self.args = args or []
        self.consecutive_failures = consecutive_failures
        self.enabled = enabled
        self.failure_threshold = failure_threshold
        self.iso_schedule = iso_schedule
        self.kwargs = kwargs or {}
        self.last_run_at = last_run_at
        self.last_updated = last_updated or time.time()
        self.name = id
        self.options = options or {}
        self.principal = principal
        self.resource = resource
        self.schedule = schedule
        self.task = task
        self.total_run_count = total_run_count

        if first_run is None:
            # get the date and time from the iso_schedule value, and if it does not have a date and
            # time, use the current date and time
            self.first_run = dateutils.format_iso8601_datetime(
                dateutils.parse_iso8601_interval(iso_schedule)[1] or
                datetime.utcnow().replace(tzinfo=isodate.UTC))
        elif isinstance(first_run, datetime):
            self.first_run = dateutils.format_iso8601_datetime(first_run)
        else:
            self.first_run = first_run
        if remaining_runs is None:
            self.remaining_runs = dateutils.parse_iso8601_interval(iso_schedule)[2]
        else:
            self.remaining_runs = remaining_runs

        self.next_run = self.calculate_next_run()

    @classmethod
    def from_db(cls, call):
        """
        Creates an instance of this class based on a document retrieved from
        the database

        :param call:    document retrieved directly from the database
        :type  call:    bson.BSON

        :return:    An instance of ScheduledCall based on the values passed in
                    the "call" object.
        :rtype:     ScheduledCall
        """
        _id = call.pop('_id', None)
        if _id:
            call['id'] = str(_id)
        call.pop('_ns', None)
        return cls(**call)

    def as_schedule_entry(self):
        """
        Creates a ScheduleEntry instance that can be used by the base scheduler
        class that comes with celery.

        :return:    a ScheduleEntry instance based on this object
        :rtype:     celery.beat.ScheduleEntry
        """
        if not self.last_run_at:
            last_run = None
        else:
            last_run = dateutils.parse_iso8601_datetime(self.last_run_at)
        #  self.schedule is cast to a string because python 2.6 sometimes fails to
        #  deserialize json from unicode.
        return ScheduleEntry(self.name, self.task, last_run, self.total_run_count,
                             pickle.loads(str(self.schedule)), self.args, self.kwargs,
                             self.options, False, scheduled_call=self)

    def as_dict(self):
        """
        Represent this object as a dictionary, which is useful for serialization.

        :return:    dictionary of public keys and values
        :rtype:     dict
        """
        return {
            '_id': str(self._id),
            'args': self.args,
            'consecutive_failures': self.consecutive_failures,
            'enabled': self.enabled,
            'failure_threshold': self.failure_threshold,
            'first_run': self.first_run,
            'kwargs': self.kwargs,
            'iso_schedule': self.iso_schedule,
            'last_run_at': self.last_run_at,
            'last_updated': self.last_updated,
            'next_run': self.calculate_next_run(),
            'principal': self.principal,
            'remaining_runs': self.remaining_runs,
            'resource': self.resource,
            'schedule': self.schedule,
            'task': self.task,
            'total_run_count': self.total_run_count,
        }

    def for_display(self):
        """
        Represent this object as a dictionary, which is useful for serializing
        to json, such as when returning this record through a REST API. This also
        removes the "principal" for security and renames "iso_schedule" to
        "schedule" for historical compatibility.

        :return:    dictionary of public keys and values minus the "principal",
                    which may be sensitive from a security standpoint, and
                    renaming "iso_schedule" to "schedule" for historical
                    compatibility.
        :rtype:     dict
        """
        ret = self.as_dict()
        del ret['principal']
        # preserving external API compatibility
        ret['schedule'] = ret.pop('iso_schedule')
        return ret

    def save(self):
        """
        Saves the current instance to the database
        """
        if self._new:
            as_dict = self.as_dict()
            as_dict['_id'] = ObjectId(as_dict['_id'])
            self.get_collection().insert(as_dict, safe=True)
            self._new = False
        else:
            as_dict = self.as_dict()
            del as_dict['_id']
            self.get_collection().update({'_id': ObjectId(self.id)}, as_dict)

    def _calculate_times(self):
        """
        Calculates and returns several time-related values that tend to be needed
        at the same time.

        :return:    tuple of numbers described below...
                    now_s: current time as seconds since the epoch
                    first_run_s: time of the first run as seconds since the epoch,
                        calculated based on self.first_run
                    since_first_s: how many seconds have elapsed since the first
                        run
                    run_every_s: how many seconds should elapse between runs of
                        this schedule
                    last_scheduled_run_s: the most recent time at which this
                        schedule should have run based on its schedule, as
                        seconds since the epoch
                    expected_runs: number of runs that should have happened based
                        on the first_run time and the interval
        :rtype:     tuple

        """
        now_s = time.time()
        first_run_dt = dateutils.to_utc_datetime(dateutils.parse_iso8601_datetime(self.first_run))
        first_run_s = calendar.timegm(first_run_dt.utctimetuple())
        since_first_s = now_s - first_run_s

        # An interval could be an isodate.Duration or a datetime.timedelta
        interval = self.as_schedule_entry().schedule.run_every
        if isinstance(interval, isodate.Duration):
            # Determine how long (in seconds) to wait between the last run and the next one. This changes
            # depending on the current time because a duration can be a month or a year.
            if self.last_run_at is not None:
                last_run_dt = dateutils.to_utc_datetime(dateutils.parse_iso8601_datetime(str(self.last_run_at)))
                run_every_s = timedelta_seconds(interval.totimedelta(start=last_run_dt))
            else:
                run_every_s = timedelta_seconds(interval.totimedelta(start=first_run_dt))

            # This discovers how many runs should have occurred based on the schedule
            expected_runs = 0
            current_run = first_run_dt
            last_scheduled_run_s = first_run_s
            duration = self.as_schedule_entry().schedule.run_every
            while True:
                # The interval is determined by the date of the previous run
                current_interval = duration.totimedelta(start=current_run)
                current_run += current_interval

                # If time of this run is less than the current time, keep going
                current_run_s = calendar.timegm(current_run.utctimetuple())
                if current_run_s < now_s:
                    expected_runs += 1
                    last_scheduled_run_s += timedelta_seconds(current_interval)
                else:
                    break
        else:
            run_every_s = timedelta_seconds(interval)
            # don't want this to be negative
            expected_runs = max(int(since_first_s / run_every_s), 0)
            last_scheduled_run_s = first_run_s + expected_runs * run_every_s

        return now_s, first_run_s, since_first_s, run_every_s, last_scheduled_run_s, expected_runs

    def calculate_next_run(self):
        """
        This algorithm starts by determining when the first call was or should
        have been. If that is in the future, it just returns that time. If not,
        it adds as many intervals as it can without exceeding the current time,
        adds one more interval, and returns the result.

        For a schedule with no historically-recorded or scheduled start time,
        it will run immediately.

        :return:    ISO8601 string representing the next time this call should run.
        :rtype:     str
        """
        now_s, first_run_s, since_first_s, run_every_s, \
            last_scheduled_run_s, expected_runs = self._calculate_times()

        # if first run is in the future, return that time
        if first_run_s > now_s:
            next_run_s = first_run_s
        # if I've never run before and my first run is not in the future, run now!
        elif self.total_run_count == 0:
            next_run_s = now_s
        else:
            next_run_s = last_scheduled_run_s + run_every_s

        return dateutils.format_iso8601_utc_timestamp(next_run_s)


class ScheduleEntry(beat.ScheduleEntry):
    def __init__(self, *args, **kwargs):
        """
        This saves the "scheduled_call" argument on the current instance,
        removes it from kwargs, and passes what is left into the superclass
        constructor.

        :param scheduled_call:  the scheduled call that produced this instance
        :type  scheduled_call:  pulp.server.db.model.dispatch.ScheduledCall
        """
        self._scheduled_call = kwargs.pop('scheduled_call')
        kwargs['app'] = app
        super(ScheduleEntry, self).__init__(*args, **kwargs)

    def _next_instance(self, last_run_at=None):
        """
        Returns an instance of this class with the appropriate fields incremented
        and updated to reflect that its task has been queued. The parent
        ScheduledCall gets saved to the database with these updated values.

        :param last_run_at: not used here, but it is part of the superclass
                            function signature

        :return:    a new instance of the same class, but with
                    its date and count fields updated.
        :rtype:     pulp.server.db.model.dispatch.ScheduleEntry
        """
        self._scheduled_call.last_run_at = dateutils.format_iso8601_utc_timestamp(time.time())
        self._scheduled_call.total_run_count += 1
        if self._scheduled_call.remaining_runs:
            self._scheduled_call.remaining_runs -= 1
        if self._scheduled_call.remaining_runs == 0:
            logger.info('disabling schedule with 0 remaining runs: %s' % self._scheduled_call.id)
            self._scheduled_call.enabled = False
        self._scheduled_call.save()
        return self._scheduled_call.as_schedule_entry()

    __next__ = next = _next_instance

    def is_due(self):
        """
        Determines if this schedule entry should be executed right now

        :return:    tuple where the first item is:
                        - True if this entry should be run right now, else False
                    and the second item is:
                        - number of seconds before this entry should next run,
                          not including an immediate run. Put another way, this
                          should never be 0
        :rtype:     tuple of (bool, number)
        """
        now_s, first_run_s, since_first_s, run_every_s, \
            last_scheduled_run_s, expected_runs = self._scheduled_call._calculate_times()

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


class ArchivedCall(Model, ReaperMixin):
    """
    Call history

    The documents in this collection may be reaped, so it inherits from ReaperMixin.
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


class TaskStatus(Model, ReaperMixin):
    """
    Represents current state of a task.
    The documents in this collection may be reaped, so it inherits from ReaperMixin.

    :ivar task_id:     identity of the task this status corresponds to
    :type task_id:     basestring
    :ivar task_type:   the fully qualified (package/method) type of the task
    :type task_type:   basestring
    :ivar tags:        custom tags on the task
    :type tags:        list
    :ivar state:       state of callable in its lifecycle
    :type state:       basestring
    :ivar result:      return value of the callable, if any
    :type result:      any
    :ivar exception:   Deprecated. This is always None.
    :type exception:   None
    :ivar traceback:   Deprecated. This is always None.
    :type traceback:   None
    :ivar start_time:  time the task started executing
    :type start_time:  datetime.datetime
    :ivar finish_time: time the task completed
    :type finish_time: datetime.datetime
    :ivar worker_name: The name of the worker that the Task is in
    :type worker_name: basestring
    :ivar error: Any errors or collections of errors that occurred while this task was running
    :type error: dict (created from a PulpException)
    :ivar spawned_tasks: List of tasks that were spawned during the running of this task
    :type spawned_tasks: list of str
    :ivar progress_report: A report containing information about task's progress
    :type progress_report: dict
    """

    collection_name = 'task_status'
    unique_indices = ('task_id',)
    search_indices = ('task_id', 'tags', 'state')

    def __init__(
            self, task_id, worker_name=None, tags=None, state=None, error=None, spawned_tasks=None,
            progress_report=None, task_type=None, start_time=None, finish_time=None, result=None):
        """
        Initialize the TaskStatus based on the provided attributes. All parameters besides task_id
        are optional.

        :param task_id:         identity of the task this status corresponds to
        :type  task_id:         basestring
        :param worker_name:     The name of the worker that the Task is in
        :type  worker_name:     basestring
        :param tags:            custom tags on the task
        :type  tags:            list
        :param state:           state of callable in its lifecycle
        :type  state:           basestring
        :param error:           Any errors or collections of errors that occurred while this task
                                was running
        :type  error:           dict (created from a PulpException)
        :param spawned_tasks:   List of tasks that were spawned during the running of this task
        :type  spawned_tasks:   list of basestrings
        :param progress_report: A report containing information about task's progress
        :type  progress_report: dict
        :param task_type:       the fully qualified (package/method) type of the task
        :type  task_type:       basestring
        :param start_time:      time the task started executing
        :type  start_time:      datetime.datetime
        :param finish_time:     time the task completed
        :type  finish_time:     datetime.datetime
        :param result:          return value of the callable, if any
        :type  result:          any
        """
        super(TaskStatus, self).__init__()

        self.task_id = task_id
        self.task_type = task_type
        self.state = state
        self.worker_name = worker_name
        self.tags = tags or []
        self.start_time = start_time
        self.finish_time = finish_time
        self.spawned_tasks = spawned_tasks or []
        self.progress_report = progress_report or {}
        self.result = result
        self.error = error
        # These are deprecated, and will always be None
        self.exception = None
        self.traceback = None

    def save(self, fields_to_set_on_insert=None):
        """
        Save the current state of the TaskStatus to the database, using an upsert operiation. If
        fields_to_set_on_insert is provided as a list of field names, the upsert operation will only
        set those fields if this becomes an insert operation, otherwise those fields will be
        ignored.

        :param fields_to_set_on_insert: A list of field names that should be updated with Mongo's
                                        $setOnInsert operator.
        :type  fields_to_set_on_insert: list
        """
        stuff_to_update = dict(copy.deepcopy(self))

        # Let's pop the $setOnInsert attributes out of the copy of self so that we can pass the
        # remaining attributes to the $set operator in the query below.
        fields_to_set_on_insert = fields_to_set_on_insert or []
        set_on_insert = {}
        for field in fields_to_set_on_insert:
            set_on_insert[field] = stuff_to_update.pop(field)
        task_id = stuff_to_update.pop('task_id')
        # MongoDB will be angry with us if we try to update the _id field
        stuff_to_update.pop('_id')

        update = {'$set': stuff_to_update}
        if set_on_insert:
            update['$setOnInsert'] = set_on_insert
        self.get_collection().update(
            {'task_id': task_id},
            update,
            upsert=True)
