#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
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
import itertools
import os
import pprint
import sys
import time
import types
import unittest
from pulp.common import dateutils
from datetime import datetime, timedelta

srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

import testutil

testutil.load_test_config()

from pulp.common import dateutils
from pulp.server.api.repo import RepoApi
from pulp.server.api.repo_sync_task import RepoSyncTask
from pulp.server.api.scheduled_sync import find_scheduled_task
from pulp.server.db.model.persistence import TaskSnapshot
from pulp.server.tasking.exception import NonUniqueTaskException
from pulp.server.tasking.scheduler import (
    Scheduler, ImmediateScheduler, AtScheduler, IntervalScheduler)
from pulp.server.tasking.task import (
    Task, task_waiting, task_running, task_finished, task_error, task_timed_out,
    task_canceled, task_complete_states)
from pulp.server.tasking.taskqueue.queue import TaskQueue
from pulp.server.tasking.taskqueue.storage import (
    VolatileStorage, PersistentStorage, _pickle_method, _unpickle_method)

# task test functions ---------------------------------------------------------

def noop():
    pass

def args(*args):
    assert len(args) > 0

def kwargs(**kwargs):
    assert len(kwargs) > 0

def result():
    return True

def error():
    raise Exception('Aaaargh!')

def interrupt_me():
    while True:
        time.sleep(0.5)

def wait(seconds=5):
    time.sleep(seconds)

class Class(object):
    def method(self):
        pass

# unittest classes ------------------------------------------------------------

class PersistentTaskTester(unittest.TestCase):

    def setUp(self):
        copy_reg.pickle(types.MethodType, _pickle_method, _unpickle_method)
        TaskSnapshot.get_collection().remove()
        self.rapi = RepoApi()
        self.rapi.clean()
        self.same_type_fields = ('scheduler',)


    def test_pickling_scheduled_sync(self):
        interval = dateutils.parse_iso8601_duration("PT5M")
        start_time = dateutils.parse_iso8601_datetime("2012-03-01T13:00:00Z")
        syncschedule = dateutils.format_iso8601_interval(interval, start_time=start_time)
        repo = self.rapi.create('some-id', 'some name', 'i386',
                                'http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64/',
                                sync_schedule=syncschedule)
        self.assertTrue(repo is not None)
        task = find_scheduled_task(repo['id'], '_sync')

        snapshot1 = task.snapshot()
        collection = TaskSnapshot.get_collection()
        collection.insert(snapshot1, safe=True)
        snapshot2 = TaskSnapshot(collection.find_one({'_id': snapshot1['_id']}))
        task2 = snapshot2.to_task()
        assert(task.scheduled_time == task2.scheduled_time)


    def test_sync_history(self):
        interval = dateutils.parse_iso8601_duration("PT1M")
        syncschedule = dateutils.format_iso8601_interval(interval)

        repo = self.rapi.create('xyz', 'xyz', 'i386',
                                'http://repos.fedorapeople.org/repos/pulp/pulp/fedora-14/x86_64/',
                                sync_schedule=syncschedule)
        self.assertTrue(repo is not None)
        time.sleep(5)
        print self.rapi.sync_history('xyz')

# run the unit tests ----------------------------------------------------------

if __name__ == '__main__':
    unittest.main()
