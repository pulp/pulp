# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
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

import heapq
import itertools

# storage class for in-memory task queues -------------------------------------

class VolatileStorage(object):
    """
    In memory queue storage class.
    """
    def __init__(self):
        self.__waiting_tasks = []
        self.__running_tasks = []
        self.__complete_tasks = []

    # wait queue methods

    def num_waiting(self):
        return len(self.__waiting_tasks)

    def enqueue_waiting(self, task):
        heapq.heappush(self.__waiting_tasks, task)

    def dequeue_waiting(self):
        return heapq.heappop(self.__waiting_tasks)

    def peek_waiting(self):
        return self.__waiting_tasks[0]

    # storage methods

    def store_running(self, task):
        assert task not in self.__waiting_tasks
        self.__running_tasks.append(task)

    def remove_running(self, task):
        assert task in self.__running_tasks
        self.__running_tasks.remove(task)

    def store_complete(self, task):
        assert task not in self.__waiting_tasks
        if task in self.__running_tasks:
            self.__running_tasks.remove(task)
        self.__complete_tasks.append(task)

    def remove_complete(self, task):
        assert task in self.__complete_tasks
        self.__complete_tasks.remove(task)

    # query methods

    def running_tasks(self):
        return self.__running_tasks[:]

    def complete_tasks(self):
        return self.__complete_tasks[:]

    def _all_tasks(self):
        return itertools.chain(self.__complete_tasks[:],
                               self.__running_tasks[:],
                               sorted(self.__waiting_tasks[:]))

    def find(self, criteria):
        num_criteria = len(criteria)
        tasks = []
        # reverse the order of all the tasks in order to list the newest first
        for task in reversed(list(self._all_tasks())):
            matches = 0
            for attr, value in criteria.items():
                if not hasattr(task, attr):
                    break;
                if getattr(task, attr) != value:
                    break;
                matches += 1
            if matches == num_criteria:
                tasks.append(task)
        return tasks
