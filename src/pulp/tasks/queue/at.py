#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
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

__author__ = 'Jason L Connor <jconnor@redhat.com>'

import heapq
import re
from datetime import datetime, timedelta

from pulp.tasks.queue.base import TaskQueue
from pulp.tasks.task import Task

# at time regular expressions -------------------------------------------------

_minute_spec = r'(?P<minute>[0-5][0-9])'
_twelve_hour_spec = r'(?<hour>0[1-9]|1[0-2]):%s\s+(?<ampm>am|pm)' % _minute_spec
_twentyfour_hour_spec = r'(?<hour>[01][0-9]|2[0-3]:%s' % _minute_spec
_hour_min_spec = r'(%s|%s)' % (_twelve_hour_spec,
                               _twentyfour_hour_spec)
_named_time_spec = r'(?P<named_time>midnight|noon|teatime)'
_relative_day_spec = r'(?P<relative_day>today|tomorrow)'
_time_spec = r'(%s|%s(\s+%s)?' % (_hour_min_spec,
                                  _named_time_spec,
                                  _relative_day_spec)

_day_spec = r'<?P<day>0?[1-9]|[12][0-9]|3[01])'
_weekday_spec = r'<?P<weekday>sun|mon|tue|wed|thu|fri|sat)'
_month_spec = r'(?P<month>0[1-9]|1[0-2])'
_named_month_spec = r'(?<named_month>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)'
_two_year_spec = r'(?P<twoyear>[0-9]{2})'
_four_year_spec = r'(?P<fouryear>[0-9]{4})'
_slash_date_spec = r'%s(/)?%s(/)?%s' % (_month_spec,
                                        _day_spec,
                                        _two_year_spec)
_dot_date_spec = r'%s\.%s\.%s' % (_day_spec,
                                  _month_spec,
                                  _two_year_spec)
_dash_date_spec = r'%s-%s-%s' % (_four_year_spec,
                                 _month_spec,
                                 _day_spec)
_formal_date_spec = r'%s\s+%s\s+(,\s+)?%s' % (_named_month_spec,
                                              _day_spec,
                                              _four_year_spec)
_explicit_date_spec = r'((?P<next>next)\s+)?%s' % _weekday_spec
_date_spec = r'(%s|%s|%s|%s|%s)' % (_slash_date_spec,
                                    _dot_date_spec,
                                    _dash_date_spec,
                                    _formal_date_spec,
                                    _explicit_date_spec)

_operator_spec = r'(?P<operator>\+|-)'
_units_spec = r'(?P<units>minutes|hours|days|weeks)'
_offset_spec = '%s(?<offset>[0-9]+)\s+%s' % (_operator_spec,
                                             _units_spec)

_at_spec = r'(%s|%s|%s\s+%s)(\s+%s)?' % (_time_spec,
                                         _date_spec,
                                         _time_spec,
                                         _date_spec,
                                         _offset_spec)

# at task queue ---------------------------------------------------------------

class AtSpecificationError(Exception):
    """
    Exception raised when a malformed at string is passed in
    """
    pass


class AtTaskQueue(TaskQueue):
    """
    Task queue with threaded dispatcher that fires off tasks at specific times
    that are either already attached to the task or entered when the task is
    enqueued.
    """
    time_regex = re.compile(_time_spec)
    date_regex = re.compile(_date_spec)
    offset_regex = re.compile(_offset_spec)
    at_regex = re.compile(_at_spec)
    
    def _dispatch(self):
        """
        Protected dispatch method executed by the dispatcher thread
        * check the current time
        * dispatch all tasks schedule on or before the current time
        @return: None
        """
        self._lock.acquire()
        while True:
            self._condition.wait(self.max_dispatcher_sleep)
            now = datetime.now()
            while self._wait_queue and self._wait_queue[0].next <= now:
                task = heapq.heappop(self._wait_queue)
                self._running_tasks[task.id] = task
                task.run()
                
    def finished(self, task):
        """
        Called by tasks on finishing
        @param task: Task instance
        @return: None
        """
        self._lock.acquire()
        try:
            self._finished_tasks[task.id] = self._running_tasks.pop(task.id)
            self._condition.notify()
        finally:
            self._lock.release()
            
    def _parse_at(self, at):
        """
        Protected method to parse strings compatible with the 'at' command to
        determine the next time a task should be run
        @param at: an 'at' formatted time string
        @return: datetime instance for the time specified
        """
        at = at.lowercase() # normalize string
        match = self.at_regex.match(at)
        if match is None:
            raise AtSpecificationError('Malformed at string: %s' % at)
        raise NotImplementedError()
            
    def enqueue(self, task, at=None):
        """
        Add a Task instance to the queue to be run at the given datetime or
        the task's .next datetime
        Any at or next in the past, will cause the task to be run at the
        earliest opportunity
        If the task has a valid .next field and an at is passed in, the explicit
        at takes precedence
        @param task: Task instance
        @param at: a datetime instance, a timedelta instance, or an 'at' command
                   formatted specification for a date/time
        @return: None
        """
        assert isinstance(task, Task)
        assert at is not None or task.next_time is not None
        
        # an explicit at will override an existing next_time
        next = at or task.next_time
        
        if isinstance(next, datetime):
            pass
        elif isinstance(next, timedelta):
            now = datetime.now()
            next = now + next
        elif isinstance(next, basestring):
            next = self._parse_at_string(next)
        else:
            raise TypeError('unsupported at time')
        
        task.next_time = next
        heapq.heappush(self._wait_queue, task)