# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import copy_reg
import datetime
import heapq
import itertools
import sys
import types
from gettext import gettext as _

from pymongo.errors import DuplicateKeyError

from pulp.common.dateutils import pickle_tzinfo, unpickle_tzinfo
from pulp.server.db.model.persistence import TaskSnapshot, TaskHistory
from pulp.server.tasking.exception import (
    DuplicateSnapshotError, SnapshotFailure)

# base storage class -----------------------------------------------------------

class Storage(object):

    # query methods

    def waiting_tasks(self):
        raise NotImplementedError(_('Base Storage class method called'))

    def running_tasks(self):
        raise NotImplementedError(_('Base Storage class method called'))

    def complete_tasks(self):
        raise NotImplementedError(_('Base Storage class method called'))

    def incomplete_tasks(self):
        return itertools.chain(self.waiting_tasks(), self.running_tasks())

    def all_tasks(self):
        return itertools.chain(self.incomplete_tasks(), self.complete_tasks())

    def find(self, criteria, ignore_complete=False):
        num_criteria = len(criteria)
        tasks = []
        if ignore_complete:
            search_tasks = self.incomplete_tasks()
        else:
            search_tasks = self.all_tasks()
        for task in search_tasks:
            matches = 0
            for attr, value in criteria.items():
                if not hasattr(task, attr):
                    break
                if getattr(task, attr) != value:
                    break
                matches += 1
            if matches == num_criteria:
                tasks.append(task)
        return tasks

    # wait queue methods

    def num_waiting(self):
        raise NotImplementedError(_('Base Storage class method called'))

    def enqueue_waiting(self, task):
        raise NotImplementedError(_('Base Storage class method called'))

    def dequeue_waiting(self):
        raise NotImplementedError(_('Base Storage class method called'))

    def peek_waiting(self):
        raise NotImplementedError(_('Base Storage class method called'))

    # task storage

    def remove_waiting(self, task):
        raise NotImplementedError(_('Base Storage class method called'))

    def store_running(self, task):
        raise NotImplementedError(_('Base Storage class method called'))

    def remove_running(self, task):
        raise NotImplementedError(_('Base Storage class method called'))

    def store_complete(self, task):
        raise NotImplementedError(_('Base Storage class method called'))

    def remove_complete(self, task):
        raise NotImplementedError(_('Base Storage class method called'))

# storage class for in-memory task queues --------------------------------------

class VolatileStorage(Storage):
    """
    In memory queue storage class.
    """
    def __init__(self):
        super(VolatileStorage, self).__init__()
        self.__waiting_tasks = []
        self.__running_tasks = []
        self.__complete_tasks = []

    # query methods

    def waiting_tasks(self):
        return self.__waiting_tasks[:]

    def running_tasks(self):
        return self.__running_tasks[:]

    def complete_tasks(self):
        return self.__complete_tasks[:]

    # wait queue methods

    def num_waiting(self):
        return len(self.__waiting_tasks)

    def enqueue_waiting(self, task):
        heapq.heappush(self.__waiting_tasks, task)

    def dequeue_waiting(self):
        if not self.__waiting_tasks:
            return None
        return heapq.heappop(self.__waiting_tasks)

    def peek_waiting(self):
        assert self.__waiting_tasks, 'Peek called on empty waiting queue'
        return self.__waiting_tasks[0]

    # storage methods

    def remove_waiting(self, task):
        assert task in self.__waiting_tasks, 'Task [%s] not in waiting tasks' % task.id
        self.__waiting_tasks.remove(task)
        heapq.heapify(self.__waiting_tasks)

    def store_running(self, task):
        assert task not in self.__waiting_tasks, 'Task [%s] in waiting tasks' % task.id
        assert task not in self.__complete_tasks, 'Task [%s] in complete tasks' % task.id
        self.__running_tasks.append(task)

    def remove_running(self, task):
        assert task in self.__running_tasks, 'Task [%s] not in running tasks' % task.id
        self.__running_tasks.remove(task)

    def store_complete(self, task):
        assert task not in self.__waiting_tasks, 'Task [%s] in waiting tasks' % task.id
        assert task not in self.__running_tasks, 'Task [%s] in running tasks' % task.id
        self.__complete_tasks.append(task)

    def remove_complete(self, task):
        assert task in self.__complete_tasks, 'Task [%s] not in complete tasks' % task.id
        self.__complete_tasks.remove(task)

# custom pickle and unpickle methods -------------------------------------------

def _pickle_method(method):
    func_name = method.im_func.__name__
    obj = method.im_self
    cls = method.im_class
    return _unpickle_method, (func_name, obj, cls)


def _unpickle_method(func_name, obj, cls):
    func = None
    # handle public, protected, and private method names
    lookup = func_name
    if func_name.startswith('__'):
        lookup = '_%s%s' % (cls.__name__, func_name)
    for cls in cls.mro():
        try:
            func = cls.__dict__[lookup]
        except KeyError:
            pass
        else:
            break
    if func is None:
        raise SnapshotFailure(_('Cannot convert snaphot to task: method %s not found in class %s') %
                              (func_name, cls.__name__))
    return func.__get__(obj, cls)

# snapshot storage class -------------------------------------------------------

class SnapshotStorage(VolatileStorage):
    """
    Snapshot storage class that uses volatile memory for storage and correctness
    and uses the database to persiste waiting and running tasks across reboots
    and to keep completed tasks around indefinitely for history and auditing
    purposes.
    """

    def  __init__(self):
        super(SnapshotStorage, self).__init__()
        # set custom pickling functions for snapshots
        copy_reg.pickle(types.MethodType, _pickle_method, _unpickle_method)
        copy_reg.pickle(datetime.tzinfo, pickle_tzinfo, unpickle_tzinfo)

    # database methods

    @property
    def snapshot_collection(self):
        return self.__dict__.setdefault('__snapshot_collection',
                                        TaskSnapshot.get_collection())

    @property
    def history_collection(self):
        return self.__dict__.setdefault('__history_collection',
                                        TaskHistory.get_collection())

    # running task methods

    def _snapshot_task(self, task):
        snapshot = task.snapshot()
        try:
            self.snapshot_collection.insert(snapshot, safe=True)
        except DuplicateKeyError:
            raise DuplicateSnapshotError(_('Duplicate snapshot for task %s') % str(task)), None, sys.exc_info()[2]

    def store_running(self, task):
        # create and keep a snapshot of the task that can be loaded from the
        # database and executed across reboots, server restarts, etc.
        self._snapshot_task(task)
        super(SnapshotStorage, self).store_running(task)

    # storage methods

    def remove_running(self, task):
        # the task has completed, so remove the snapshot
        self.snapshot_collection.remove({'_id': task.snapshot_id}, safe=True)
        super(SnapshotStorage, self).remove_running(task)

    def store_complete(self, task):
        history = TaskHistory(task)
        self.history_collection.insert(history)
        super(SnapshotStorage, self).store_complete(task)
