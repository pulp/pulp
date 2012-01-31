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

"""
scheduler module defining different types of Task schedulers.
"""

import datetime
import logging
import types
from gettext import gettext as _

from pulp.common import dateutils
from pulp.server.util import Singleton


class Scheduler(object):
    """
    Base Scheduler class defining the scheduler interface.
    """

    def __str__(self):
        return _('Base class scheduler with no schedule implementation')

    def schedule(self, previous_run):
        """
        Schedule the next run time of a L{Task} based upon the previous run
        time of that Task.
        @type previous_run: None or datetime.datetime instance
        @param previous_run: the previous run time of the Task,
                             None if not previously run
        @rtype: tuple of (None or int, None or datetime.datetime instance)
        @return: a tuple of (adjustments, schedule time) where adjustments is
                 the number of adjustments needed to make the schedule time
                 valid and schedule time, a datetime.datetime instance
                 representing the date and time to schedule a task run
                 a adjustments value of None means that no algorithm was
                 employed to schedule the run and a schedule value of None
                 means not to schedule the task to run
        """
        assert isinstance(previous_run, (types.NoneType, datetime.datetime))
        raise NotImplementedError('Base class Scheduler.schedule() called')


class ImmediateScheduler(Scheduler):
    """
    Immediate Scheduler that schedules a Task to run immediately and only once.
    """

    __metaclass__ = Singleton

    def __str__(self):
        return _('scheduled to run immediately')

    def schedule(self, previous_run):
        assert isinstance(previous_run, (types.NoneType, datetime.datetime))
        if previous_run is None:
            return (None, datetime.datetime.now(dateutils.utc_tz()))
        return (None, None)


class AtScheduler(Scheduler):
    """
    At Scheduler (as in the command line utility: at) that schedules a Task to
    run once at some arbitrary point in the future.
    """
    def __init__(self, scheduled_time):
        """
        @type scheduled_time: datetime.datetime instance
        @param scheduled_time: time to run the task
        @raise ValueError: if scheduled_time is in the past
        """
        assert isinstance(scheduled_time, datetime.datetime)
        if scheduled_time < datetime.datetime.now(dateutils.local_tz()):
            raise ValueError('AtScheduler: scheduled time is in the past: %s' %
                             str(scheduled_time))
        self.scheduled_time = dateutils.to_utc_datetime(scheduled_time)

    def __str__(self):
        return _('scheduled to run at %s') % \
                self.scheduled_time.strftime('%Y-%m-%d %H:%M %z')

    def schedule(self, previous_run):
        assert isinstance(previous_run, (types.NoneType, datetime.datetime))
        if previous_run is None:
            return (None, self.scheduled_time)
        return (None, None)


class IntervalScheduler(Scheduler):
    """
    Interval Scheduler that will run a Task ad infinitum or a finite number of
    times from a given start time at a specified time interval.
    """
    def __init__(self, interval, start_time=None, runs=None):
        """
        @type interval: datetime.timedelta instance
        @param interval: the time span between task runs
        @type start_time: datetime.datetime instance or None (default)
        @param start_time: the time of the first run, immediately if None
        @type runs: int or None (default)
        @param runs: the total number of task runs, ad infinitum if None
        @raise ValueError: if start_time is not None and is in the past
        """
        assert isinstance(interval, datetime.timedelta)
        assert isinstance(start_time, (types.NoneType, datetime.datetime))
        assert isinstance(runs, (types.NoneType, int))
        if start_time is not None and \
                start_time < datetime.datetime.now(dateutils.local_tz()) - interval:
            log = logging.getLogger('pulp')
            log.warn(_('IntervalScheduler created with start time more than one interval in the past: %s, %s') %
                     (str(start_time), str(interval)))
        self.interval = interval
        self.start_time = start_time and dateutils.to_utc_datetime(start_time)
        self.remaining_runs = runs

    def __str__(self):

        def _start_time():
            if self.start_time is None:
                return 'immediately'
            return 'at %s' % self.start_time.strftime('%Y-%m-%d %H:%M %z')

        def _num_runs():
            if self.remaining_runs is None:
                return 'indefinitely'
            return 'for %d more runs' % self.remaining_runs

        def _next_run():
            if self.remaining_runs == 0:
                return 'not scheduled'
            next = self._next_run(self.start_time)[1]
            return 'scheduled to run at %s' % next.strftime('%Y-%m-%d %H:%M %z')

        return _('scheduled to run starting %s at intervals %s long %s; next run %s') % \
                (_start_time(), str(self.interval), _num_runs(), _next_run())

    def _next_run(self, reference_time):
        # guarantee that the next run is scheduled in the future
        # and count the number of intervals that had to be added to make it in
        # the future for catching and reporting tasks that take longer than
        # their scheduled intervals
        now = datetime.datetime.now(dateutils.utc_tz())
        reference_time = reference_time or now
        intervals = 0
        while reference_time < now:
            reference_time += self.interval
            intervals += 1
        return (intervals, reference_time)

    def schedule(self, previous_run):
        # NOTE to prevent interval "drift" the previous_run value should be the
        # scheduled time for the previous run instead of the actual start time
        assert isinstance(previous_run, (types.NoneType, datetime.datetime))
        if self.remaining_runs == 0:
            return (None, None)
        if self.remaining_runs:
            self.remaining_runs -= 1
        if previous_run is None:
            return self._next_run(self.start_time)
        return self._next_run(previous_run)
