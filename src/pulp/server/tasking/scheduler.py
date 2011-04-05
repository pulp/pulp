# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

"""
scheduler module defining different types of Task schedulers.
Note: all times in this module use the UTC timezone.
"""

import datetime
import logging
import types
from gettext import gettext as _

from pulp.server.util import Singleton


class Scheduler(object):
    """
    Base Scheduler class defining the scheduler interface.
    """
    def schedule(self, previous_run):
        """
        Schedule the next run time of a L{Task} based upon the previous run
        time of that Task.
        @type previous_run: None or datetime.datetime instance
        @param previous_run: the previous run time of the Task,
                             None if not previously run
        """
        assert isinstance(previous_run, (types.NoneType, datetime.datetime))
        raise NotImplementedError('Base class Scheduler.schedule() called')


class ImmediateScheduler(Scheduler):
    """
    Immediate Scheduler that schedules a Task to run immediately and only once.
    """

    __metaclass__ = Singleton

    def schedule(self, previous_run):
        assert isinstance(previous_run, (types.NoneType, datetime.datetime))
        if previous_run is None:
            return datetime.datetime.utcnow()
        return None


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
        if scheduled_time < datetime.datetime.utcnow():
            raise ValueError('AtScheduler: scheduled time in the past: %s' %
                             str(scheduled_time))
        self.scheduled_time = scheduled_time

    def schedule(self, previous_run):
        assert isinstance(previous_run, (types.NoneType, datetime.datetime))
        if previous_run is None:
            return self.scheduled_time
        return None


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
                start_time < datetime.datetime.utcnow() - interval:
            log = logging.getLogger('pulp')
            log.warn(_('IntervalScheduler created with start time more than one interval in the past: %s, %s') %
                     str(start_time), str(interval))
        self.interval = interval
        self.start_time = start_time
        self.remaining_runs = runs

    def schedule(self, previous_run):
        # NOTE to prevent interval "drift" the previous_run value should be the
        # scheduled time for the previous run instead of the actual start time
        assert isinstance(previous_run, (types.NoneType, datetime.datetime))

        # guarantee that the next run is scheduled in the future
        # and count the number of intervals that had to be added to make it in
        # the future for catching and reporting tasks that take longer than
        # their scheduled intervals
        def _next_run(reference_time):
            now = datetime.datetime.utcnow()
            reference_time = reference_time or now
            intervals = 0
            while reference_time < now:
                reference_time += self.interval
                intervals += 1
            return (intervals, reference_time)

        if self.remaining_runs == 0:
            return None
        if self.remaining_runs:
            self.remaining_runs -= 1
        if previous_run is None:
            return _next_run(self.start_time)[1]
        return _next_run(previous_run)[1]
