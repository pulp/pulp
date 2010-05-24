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

_inc_or_dec = r''
_date = r''
_time = r''
_spec_base = r'(%s|%s|%s\s+%s|(?P<now>now)' % (_date, _time, _time, _date)
_at_time_spec = r'^%s(\s+%s)?' % (_spec_base, _inc_or_dec)

# at task queue ---------------------------------------------------------------

class AtTaskQueue(TaskQueue):
    """
    """
    at_regex = re.compile(_at_time_spec)
    
    def _dispatch(self):
        """
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
        """
        self._lock.acquire()
        try:
            self._finished_tasks[task.id] = self._running_tasks.pop(task.id)
            self._condition.notify()
        finally:
            self._lock.release()
            
    def _parse_at_string(self, atstr):
        raise NotImplementedError()
            
    def enqueue(self, task, at=None):
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