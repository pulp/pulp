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

import copy_reg
import datetime
import heapq
import itertools
import types
from gettext import gettext as _

from pulp.common.dateutils import pickle_tzinfo, unpickle_tzinfo
from pulp.server.db.model.persistence import TaskSnapshot, TaskHistory
from pulp.server.tasking.task import (
    task_running, task_ready_states, task_complete_states, task_waiting,
    task_states)
from pulp.server.util import Singleton

# base storage class -----------------------------------------------------------

class Storage(object):

    # query methods

    def waiting_tasks(self):
        raise NotImplementedError(_('Base Storage class method called'))

    def running_tasks(self):
        raise NotImplementedError(_('Base Storage class method called'))

    def complete_tasks(self):
        raise NotImplementedError(_('Base Storage class method called'))

    def all_tasks(self):
        return itertools.chain(self.waiting_tasks(),
                               self.running_tasks(),
                               self.complete_tasks())

    def find(self, criteria):
        num_criteria = len(criteria)
        tasks = []
        for task in self.all_tasks():
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

    # wait queue methods

    def num_waiting(self):
        raise NotImplementedError(_('Base Storage class method called'))

    def enqueue_waiting(self, task):
        raise NotImplementedError(_('Base Storage class method called'))

    def dequeue_waiting(self):
        raise NotImplementedError(_('Base Storage class method called'))

    def peek_waiting(self):
        raise NotImplemented(_('Base Storage class method called'))

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
        assert self.__waiting_tasks
        return self.__waiting_tasks[0]

    # storage methods

    def remove_waiting(self, task):
        assert task in self.__waiting_tasks
        self.__waiting_tasks.remove(task)
        heapq.heapify(self.__waiting_tasks)

    def store_running(self, task):
        assert task not in self.__waiting_tasks
        assert task not in self.__complete_tasks
        self.__running_tasks.append(task)

    def remove_running(self, task):
        assert task in self.__running_tasks
        self.__running_tasks.remove(task)

    def store_complete(self, task):
        assert task not in self.__waiting_tasks
        assert task not in self.__running_tasks
        self.__complete_tasks.append(task)

    def remove_complete(self, task):
        assert task in self.__complete_tasks
        self.__complete_tasks.remove(task)

# custom pickle and unpickle methods -------------------------------------------

def _pickle_method(method):
    func_name = method.im_func.__name__
    obj = method.im_self
    cls = method.im_class
    return _unpickle_method, (func_name, obj, cls)


def _unpickle_method(func_name, obj, cls):
    for cls in cls.mro():
        try:
            func = cls.__dict__[func_name]
        except KeyError:
            pass
        else:
            break
    return func.__get__(obj, cls)

# storage class for database-stored tasks --------------------------------------

class PersistentStorage(Storage):

    __metaclass__ = Singleton

    def __init__(self):
        super(PersistentStorage, self).__init__()
        copy_reg.pickle(types.MethodType, _pickle_method, _unpickle_method)
        copy_reg.pickle(datetime.tzinfo, pickle_tzinfo, unpickle_tzinfo)

    # database methods

    @property
    def collection(self):
        return self.__dict__.setdefault('_collection', TaskSnapshot.get_collection())

    def __store_task(self, task):
        self.collection.save(task.snapshot(), safe=True)

    def __tasks_with_states(self, states):
        return self.collection.find({'state': {'$in': list(states)}})

    def __cursor_to_tasks(self, cursor):
        return [TaskSnapshot(s).to_task() for s in cursor]

    def __waiting_tasks(self):
        return self.__tasks_with_states(task_ready_states)

    def __running_tasks(self):
        return self.__tasks_with_states((task_running))

    def __complete_tasks(self):
        return self.__tasks_with_states(task_complete_states)

    def __all_tasks(self):
        return self.__tasks_with_states(task_states)

    # query methods

    def waiting_tasks(self):
        return self.__cursor_to_tasks(self.__waiting_tasks())

    def running_tasks(self):
        return self.__cursor_to_tasks(self.__running_tasks())

    def complete_tasks(self):
        return self.__cursor_to_tasks(self.__complete_tasks())

    def all_tasks(self):
        return self.__cursor_to_tasks(self.__all_tasks())

    def find(self, criteria):
        # provided here in case we want to override this
        return super(PersistentStorage, self).find(criteria)

    # wait queue methods

    def num_waiting(self):
        return self.__waiting_tasks().count()

    def enqueue_waiting(self, task):
        assert task.state == task_waiting, \
               'task %s enqueued with state %s' % (task, task.state)
        assert task.scheduled_time is not None, \
               'task %s enqueued with None scheduld_time' % task
        self.__store_task(task)

    def dequeue_waiting(self):
        snapshots = self.__waiting_tasks().sort('scheduled_time').limit(1)
        if snapshots.count() == 0:
            return None
        snapshot = snapshots[0]
        task = TaskSnapshot(snapshot).to_task()
        self.remove_waiting(task)
        return task

    def peek_waiting(self):
        snapshots = self.__waiting_tasks().sort('scheduled_time').limit(1)
        if snapshots.count() == 0:
            return None
        return TaskSnapshot(snapshots[0]).to_task()

    # storage methods

    def remove_waiting(self, task):
        self.collection.remove({'id': task.id, 'state': task_waiting})

    def store_running(self, task):
        # because we are storing snapshots and the task is no longer stored in
        # volatile memory, there is a disconnect between when a task sets itself
        # as running and when it gets recorded in the db as running
        # so we accept tasks that are still in a ready state and set them to the
        # running state, this is a little bit wrong, but unavoidable given the
        # current control flow
        assert str(task.state) in (task_waiting, task_running), \
               'task %s with state %s stored as running' % (task, task.state)
        if task.state == task_waiting:
            task.state = task_running
        self.__store_task(task)

    def remove_running(self, task):
        self.collection.remove({'id': task.id, 'state': task_running})

    def store_complete(self, task):
        assert str(task.state) in task_complete_states, \
               'task %s with state %s stored as complete' % (task, task.state)
        self.__store_task(task)

    def remove_complete(self, task):
        # as we're storing multiple copies of each task in the complete state,
        # this method is now a noop because there's not enough information
        # provided to decided on which copy to delete
        pass

# hybrid storage class ---------------------------------------------------------

class HybridStorage(VolatileStorage):
    """
    Hybrid storage class that uses volatile memory for storage and correctness
    and uses the database to persiste waiting and running tasks across reboots
    and to keep completed tasks around indefinitely for history and auditing
    purposes.
    """

    def  __init__(self):
        super(HybridStorage, self).__init__()
        # set custom pickling functions for snapshots
        copy_reg.pickle(types.MethodType, _pickle_method, _unpickle_method)
        copy_reg.pickle(datetime.tzinfo, pickle_tzinfo, unpickle_tzinfo)
        # load existing incomplete tasks from the database on initialization
        for snapshot in self.snapshot_collection.find():
            task = TaskSnapshot(snapshot).to_task()
            # tasks are already in the database, so just enqueue them in memory
            super(HybridStorage, self).enqueue_waiting(task)

    # database methods

    @property
    def snapshot_collection(self):
        return self.__dict__.setdefault('__snapshot_collection',
                                        TaskSnapshot.get_collection())

    @property
    def history_collection(self):
        return self.__dict__.setdefault('__history_collection',
                                        TaskHistory.get_collection())

    # wait queueue methods

    def enqueue_waiting(self, task):
        super(HybridStorage, self).enqueue_waiting(task)
        # create and keep a snapshot of the task that can be loaded from the
        # database and executed across reboots, server restarts, etc.
        snapshot = task.snapshot()
        self.snapshot_collection.insert(snapshot)

    # storage methods

    def remove_running(self, task):
        super(HybridStorage, self).remove_running(task)
        # the task has completed, so remove the snapshot
        self.snapshot_collection.remove({'id': task.snapshot_id})

    def store_complete(self, task):
        super(HybridStorage, self).store_complete(task)
        history = TaskHistory(task)
        self.history_collection.insert(history)
