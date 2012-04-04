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

import datetime
import os
import sys
import threading
import traceback

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + '/../common/')

try:
    from bson.objectid import ObjectId
except ImportError:
    from pymongo.objectid import ObjectId

import mock
import testutil

from pulp.common import dateutils
from pulp.server.db.model.dispatch import ScheduledCall
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import pickling
from pulp.server.dispatch.call import CallReport, CallRequest, ScheduledCallRequest
from pulp.server.dispatch.coordinator import Coordinator
from pulp.server.dispatch.scheduler import Scheduler
from pulp.server.dispatch.taskqueue import TaskQueue

# test data --------------------------------------------------------------------

def call(*args, **kwargs):
    pass

SCHEDULE_3_RUNS = 'R3/PT30M'
SCHEDULE_0_RUNS = 'R0/P1D'
SCHEDULE_INDEFINITE_RUNS = 'PT12H'
SCHEDULE_START_TIME = '2012-01-26T23:01:30-07:00/PT12H'
DISPATCH_SCHEDULE = 'R2/PT0S'
DISPATCH_FUTURE_SCHEDULE = '3000-01-01T00:00:01/PT1H'

# scheduler instantiation ------------------------------------------------------

class SchedulerInstantiationTests(testutil.PulpTest):

    def test_instantiation(self):
        try:
            Scheduler(Coordinator(TaskQueue(0)))
        except:
            self.fail(traceback.format_exc())

    def test_start_stop(self):
        scheduler = Scheduler(Coordinator(TaskQueue(0)),dispatch_interval=1)
        self.assertTrue(scheduler._Scheduler__dispatcher is None)
        scheduler.start()
        self.assertTrue(isinstance(scheduler._Scheduler__dispatcher, threading.Thread))
        scheduler.stop()
        self.assertTrue(scheduler._Scheduler__dispatcher is None)

# scheduler testing ------------------------------------------------------------

class SchedulerTests(testutil.PulpTest):

    def setUp(self):
        super(SchedulerTests, self).setUp()
        pickling.initialize()
        self.scheduler = Scheduler(coordinator=Coordinator(TaskQueue(0)))
        # replace the coordinator so we do not actually execute tasks
        self.scheduler.coordinator = mock.Mock()
        # NOTE we are not starting the scheduler

    def tearDown(self):
        super(SchedulerTests, self).tearDown()
        ScheduledCall.get_collection().drop()
        self.scheduler = None

# scheduled call control tests -------------------------------------------------

class SchedulerCallControlTests(SchedulerTests):

    def test_add(self):
        call_request = CallRequest(call)
        scheduled_call_request = ScheduledCallRequest(call_request, SCHEDULE_3_RUNS)
        schedule_id = self.scheduler.add(scheduled_call_request)
        collection = ScheduledCall.get_collection()
        scheduled_call = collection.find_one({'_id': ObjectId(schedule_id)})
        self.assertFalse(scheduled_call is None)

    def test_add_no_runs(self):
        call_request = CallRequest(call)
        scheduled_call_request = ScheduledCallRequest(call_request, SCHEDULE_0_RUNS)
        schedule_id = self.scheduler.add(scheduled_call_request)
        self.assertTrue(schedule_id is None)
        collection = ScheduledCall.get_collection()
        cursor = collection.find()
        self.assertTrue(cursor.count() == 0)

    def test_remove(self):
        call_request = CallRequest(call)
        scheduled_call_request = ScheduledCallRequest(call_request, SCHEDULE_START_TIME)
        schedule_id = self.scheduler.add(scheduled_call_request)
        self.scheduler.remove(schedule_id)
        collection = ScheduledCall.get_collection()
        scheduled_call = collection.find_one({'_id': schedule_id})
        self.assertTrue(scheduled_call is None)

    def test_disable_enable(self):
        call_request = CallRequest(call)
        scheduled_call_request = ScheduledCallRequest(call_request, SCHEDULE_3_RUNS)
        schedule_id = self.scheduler.add(scheduled_call_request)
        collection = ScheduledCall.get_collection()
        scheduled_call = collection.find_one({'_id': ObjectId(schedule_id)})
        self.assertTrue(scheduled_call['enabled'])
        self.scheduler.disable(schedule_id)
        scheduled_call = collection.find_one({'_id': ObjectId(schedule_id)})
        self.assertFalse(scheduled_call['enabled'])
        self.scheduler.enable(schedule_id)
        scheduled_call = collection.find_one({'_id': ObjectId(schedule_id)})
        self.assertTrue(scheduled_call['enabled'])

# dispatch control flow tests --------------------------------------------------

class SchedulerDispatchControlFlowTests(SchedulerTests):

    def test_run_scheduled_calls(self):
        scheduled_call_request = ScheduledCallRequest(CallRequest(call), DISPATCH_SCHEDULE)
        self.scheduler.add(scheduled_call_request)
        self.scheduler._run_scheduled_calls()
        self.assertTrue(self.scheduler.coordinator.execute_call_asynchronously.call_count == 1)

    def test_run_scheduled_calls_multiple_calls(self):
        self.scheduler.add(ScheduledCallRequest(CallRequest(call), DISPATCH_SCHEDULE))
        self.scheduler.add(ScheduledCallRequest(CallRequest(call), DISPATCH_FUTURE_SCHEDULE))
        self.scheduler._run_scheduled_calls()
        self.assertTrue(self.scheduler.coordinator.execute_call_asynchronously.call_count == 1)

# scheduling tests -------------------------------------------------------------

class SchedulerSchedulingTests(SchedulerTests):

    def test_update_last_run_success(self):
        call_request = CallRequest(call)
        call_report = CallReport(state=dispatch_constants.CALL_FINISHED_STATE)
        scheduled_call_request = ScheduledCallRequest(call_request, DISPATCH_SCHEDULE)
        schedule_id = self.scheduler.add(scheduled_call_request)
        scheduled_call = self.scheduler.scheduled_call_collection.find_one({'_id': ObjectId(schedule_id)})
        self.assertTrue(scheduled_call['last_run'] == None)
        self.assertTrue(scheduled_call['remaining_runs'] == 2)
        self.scheduler.update_last_run(scheduled_call, call_report)
        updated_scheduled_call = self.scheduler.scheduled_call_collection.find_one({'_id': ObjectId(schedule_id)})
        # relies on schedule's 0 length interval and initially having 2 runs
        self.assertTrue(updated_scheduled_call['last_run'] == updated_scheduled_call['next_run'])
        self.assertTrue(updated_scheduled_call['remaining_runs'] == 1)

    def test_update_last_run_failure(self):
        call_request = CallRequest(call)
        call_report = CallReport(state=dispatch_constants.CALL_ERROR_STATE)
        scheduled_call_request = ScheduledCallRequest(call_request, DISPATCH_SCHEDULE, failure_threshold=1)
        schedule_id = self.scheduler.add(scheduled_call_request)
        scheduled_call = self.scheduler.scheduled_call_collection.find_one({'_id': ObjectId(schedule_id)})
        self.assertTrue(scheduled_call['consecutive_failures'] == 0)
        self.assertTrue(scheduled_call['enabled'])
        self.scheduler.update_last_run(scheduled_call, call_report)
        updated_scheduled_call = self.scheduler.scheduled_call_collection.find_one({'_id': ObjectId(schedule_id)})
        self.assertTrue(updated_scheduled_call['consecutive_failures'] == 1)
        # scheduled call should be disabled because failure_threshold was set to 1
        self.assertFalse(updated_scheduled_call['enabled'])

    def test_calculate_next_run(self):
        call_request = CallRequest(call)
        interval = datetime.timedelta(minutes=1)
        schedule = dateutils.format_iso8601_interval(interval)
        scheduled_call_request = ScheduledCallRequest(call_request, schedule)
        scheduled_id = self.scheduler.add(scheduled_call_request)
        scheduled_call = self.scheduler.scheduled_call_collection.find_one({'_id': ObjectId(scheduled_id)})
        next_run = self.scheduler.calculate_next_run(scheduled_call)
        self.assertFalse(next_run is None)
        self.assertTrue(next_run == scheduled_call['start_date'])
        self.scheduler.update_last_run(scheduled_call)
        updated_scheduled_call = self.scheduler.scheduled_call_collection.find_one({'_id': ObjectId(scheduled_id)})
        updated_next_run = self.scheduler.calculate_next_run(updated_scheduled_call)
        self.assertTrue(updated_next_run == interval + updated_scheduled_call['last_run'])

# query tests ------------------------------------------------------------------

class SchedulerQueryTests(SchedulerTests):

    def setUp(self):
        super(SchedulerQueryTests, self).setUp()
        self.scheduler._run_method = call

    def test_get(self):
        call_request_1 = CallRequest(call)
        schedule_id = self.scheduler.add(ScheduledCallRequest(call_request_1, SCHEDULE_3_RUNS))
        self.assertFalse(schedule_id is None)
        scheduled_call_request = self.scheduler.get(schedule_id)
        self.assertFalse(scheduled_call_request.schedule is None)
        self.assertFalse(scheduled_call_request.call_request is None)
        self.assertTrue(call_request_1.call == scheduled_call_request.call_request.call)
        self.assertTrue(call_request_1.args == scheduled_call_request.call_request.args)
        self.assertTrue(call_request_1.kwargs == scheduled_call_request.call_request.kwargs)
        self.assertTrue(SCHEDULE_3_RUNS == scheduled_call_request.schedule)

    def test_find_single_tag(self):
        tag = 'TAG'
        call_request_1 = CallRequest(call)
        call_request_1.tags.append(tag)
        id_1 = self.scheduler.add(ScheduledCallRequest(call_request_1, SCHEDULE_INDEFINITE_RUNS))
        call_list = self.scheduler.find(tag)
        self.assertTrue(len(call_list) == 1)

