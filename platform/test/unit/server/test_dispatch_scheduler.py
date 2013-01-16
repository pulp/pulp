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
import threading
import traceback

import isodate
import mock

from pulp.common import dateutils
from pulp.server.compat import ObjectId
from pulp.server.db.model.dispatch import ScheduledCall
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.dispatch import pickling
from pulp.server.dispatch.call import CallReport, CallRequest
from pulp.server.dispatch.scheduler import Scheduler, scheduler_complete_callback

import base

# test data --------------------------------------------------------------------

def itinerary_call(*args, **kwargs):
    def _call(*args, **kwargs):
        pass
    call_request = CallRequest(_call, args, kwargs)
    return [call_request]

def dummy_call():
    pass

SCHEDULE_3_RUNS = 'R3/PT30M'
SCHEDULE_0_RUNS = 'R0/P1D'
SCHEDULE_INDEFINITE_RUNS = 'PT12H'
SCHEDULE_START_TIME = '2012-01-26T23:01:30-07:00/PT12H'
DISPATCH_SCHEDULE = 'R2/PT0S'
DISPATCH_FUTURE_SCHEDULE = '3000-01-01T00:00:01/PT1H'

# scheduler instantiation ------------------------------------------------------

class SchedulerInstantiationTests(base.PulpServerTests):

    def test_instantiation(self):
        try:
            Scheduler()
        except:
            self.fail(traceback.format_exc())

    def test_start_stop(self):
        scheduler = Scheduler(dispatch_interval=1)
        self.assertTrue(scheduler._Scheduler__dispatcher is None)
        scheduler.start()
        self.assertTrue(isinstance(scheduler._Scheduler__dispatcher, threading.Thread))
        scheduler.stop()
        self.assertTrue(scheduler._Scheduler__dispatcher is None)

# scheduler testing ------------------------------------------------------------

class SchedulerTests(base.PulpServerTests):

    def setUp(self):
        super(SchedulerTests, self).setUp()
        pickling.initialize()

        self.scheduler = Scheduler() # NOTE we are not starting the scheduler
        self.scheduled_call_collection = ScheduledCall.get_collection()

        # replace the coordinator so we do not actually execute tasks
        self._coordinator_factory = dispatch_factory.coordinator
        dispatch_factory.coordinator = mock.Mock()

        # replace the scheduler with ours
        dispatch_factory._SCHEDULER = self.scheduler

    def tearDown(self):
        super(SchedulerTests, self).tearDown()
        ScheduledCall.get_collection().drop()
        self.scheduler = None
        dispatch_factory.coordinator = self._coordinator_factory
        self._coordinator_factory = None
        dispatch_factory._SCHEDULER = None

# scheduled call control tests -------------------------------------------------

class SchedulerCallControlTests(SchedulerTests):

    def test_add(self):
        call_request = CallRequest(itinerary_call)
        schedule_id = self.scheduler.add(call_request, SCHEDULE_3_RUNS)
        collection = ScheduledCall.get_collection()
        scheduled_call = collection.find_one({'_id': ObjectId(schedule_id)})
        self.assertFalse(scheduled_call is None)

    def test_add_no_runs(self):
        call_request = CallRequest(itinerary_call)
        schedule_id = self.scheduler.add(call_request, SCHEDULE_0_RUNS)
        self.assertTrue(schedule_id is None)
        collection = ScheduledCall.get_collection()
        cursor = collection.find()
        self.assertTrue(cursor.count() == 0)

    def test_remove(self):
        call_request = CallRequest(itinerary_call)
        schedule_id = self.scheduler.add(call_request, SCHEDULE_START_TIME)
        self.scheduler.remove(schedule_id)
        collection = ScheduledCall.get_collection()
        scheduled_call = collection.find_one({'_id': schedule_id})
        self.assertTrue(scheduled_call is None)

    def test_disable_enable(self):
        call_request = CallRequest(itinerary_call)
        schedule_id = self.scheduler.add(call_request, SCHEDULE_3_RUNS)
        collection = ScheduledCall.get_collection()
        scheduled_call = collection.find_one({'_id': ObjectId(schedule_id)})
        self.assertTrue(scheduled_call['enabled'])
        self.scheduler.disable(schedule_id)
        scheduled_call = collection.find_one({'_id': ObjectId(schedule_id)})
        self.assertFalse(scheduled_call['enabled'])
        self.scheduler.enable(schedule_id)
        scheduled_call = collection.find_one({'_id': ObjectId(schedule_id)})
        self.assertTrue(scheduled_call['enabled'])

    def test_complete_callback(self):
        scheduled_call_request = CallRequest(itinerary_call)
        schedule_id = self.scheduler.add(scheduled_call_request, SCHEDULE_3_RUNS)

        run_call_request = scheduled_call_request.call()[0]
        run_call_report = CallReport.from_call_request(run_call_request)
        run_call_report.schedule_id = schedule_id

        scheduler_complete_callback(run_call_request, run_call_report)

        collection = ScheduledCall.get_collection()
        scheduled_call = collection.find_one({'_id': ObjectId(schedule_id)})

        self.assertNotEqual(scheduled_call['last_run'], None)

    def test_complete_callback_missing_schedule(self):
        scheduled_call_request = CallRequest(itinerary_call)
        schedule_id = self.scheduler.add(scheduled_call_request, SCHEDULE_3_RUNS)

        run_call_request = scheduled_call_request.call()[0]
        run_call_report = CallReport.from_call_request(run_call_request)
        run_call_report.schedule_id = schedule_id

        collection = ScheduledCall.get_collection()
        collection.remove({'_id': ObjectId(schedule_id)}, safe=True)

        try:
            scheduler_complete_callback(run_call_request, run_call_report)
        except:
            self.fail()

# scheduling tests -------------------------------------------------------------

class SchedulerSchedulingTests(SchedulerTests):

    def test_update_last_run_success(self):
        call_request = CallRequest(itinerary_call)
        call_report = CallReport(state=dispatch_constants.CALL_FINISHED_STATE)
        schedule_id = self.scheduler.add(call_request, DISPATCH_SCHEDULE)
        scheduled_call = self.scheduled_call_collection.find_one({'_id': ObjectId(schedule_id)})
        self.assertTrue(scheduled_call['last_run'] == None)
        self.assertTrue(scheduled_call['remaining_runs'] == 2)
        self.scheduler.update_last_run(scheduled_call, call_report)
        updated_scheduled_call = self.scheduled_call_collection.find_one({'_id': ObjectId(schedule_id)})
        # relies on schedule's 0 length interval and initially having 2 runs
        self.assertTrue(updated_scheduled_call['last_run'] == updated_scheduled_call['next_run'])
        self.assertTrue(updated_scheduled_call['remaining_runs'] == 1)

    def test_update_last_run_failure(self):
        call_request = CallRequest(itinerary_call)
        call_report = CallReport(state=dispatch_constants.CALL_ERROR_STATE)
        schedule_id = self.scheduler.add(call_request, DISPATCH_SCHEDULE, failure_threshold=1)
        scheduled_call = self.scheduled_call_collection.find_one({'_id': ObjectId(schedule_id)})
        self.assertTrue(scheduled_call['consecutive_failures'] == 0)
        self.assertTrue(scheduled_call['enabled'])
        self.scheduler.update_last_run(scheduled_call, call_report)
        updated_scheduled_call = self.scheduled_call_collection.find_one({'_id': ObjectId(schedule_id)})
        self.assertTrue(updated_scheduled_call['consecutive_failures'] == 1)
        # scheduled call should be disabled because failure_threshold was set to 1
        self.assertFalse(updated_scheduled_call['enabled'])

    def test_calculate_next_run(self):
        call_request = CallRequest(itinerary_call)
        interval = datetime.timedelta(minutes=1)
        schedule = dateutils.format_iso8601_interval(interval)
        scheduled_id = self.scheduler.add(call_request, schedule)
        scheduled_call = self.scheduled_call_collection.find_one({'_id': ObjectId(scheduled_id)})
        next_run = self.scheduler.calculate_next_run(scheduled_call)
        self.assertFalse(next_run is None)
        self.assertTrue(next_run == scheduled_call['first_run'])
        self.scheduler.update_last_run(scheduled_call)
        updated_scheduled_call = self.scheduled_call_collection.find_one({'_id': ObjectId(scheduled_id)})
        updated_next_run = self.scheduler.calculate_next_run(updated_scheduled_call)
        self.assertTrue(updated_next_run == updated_scheduled_call['last_run'])

    def test_calculate_next_run_duration(self):
        call_request = CallRequest(itinerary_call)
        now = datetime.datetime.now()
        interval = isodate.Duration(months=1)
        schedule = dateutils.format_iso8601_interval(interval, now)
        schedule_id = self.scheduler.add(call_request, schedule)
        scheduled_call = self.scheduled_call_collection.find_one({'_id': ObjectId(schedule_id)})
        next_run = self.scheduler.calculate_next_run(scheduled_call)
        self.assertFalse(next_run is None)
        self.assertTrue(next_run == scheduled_call['first_run'])
        self.scheduler.update_last_run(scheduled_call)
        updated_scheduled_call = self.scheduled_call_collection.find_one({'_id': ObjectId(schedule_id)})
        updated_next_run = self.scheduler.calculate_next_run(updated_scheduled_call)
        self.assertTrue(updated_next_run == updated_scheduled_call['last_run'])

    def test_next_run_updated(self):
        call_request = CallRequest(itinerary_call)
        now = datetime.datetime.now()
        interval = datetime.timedelta(minutes=1)
        schedule = dateutils.format_iso8601_interval(interval, now)
        schedule_id = self.scheduler.add(call_request, schedule)

        scheduled_call = self.scheduled_call_collection.find_one({'_id': ObjectId(schedule_id)})
        next_next_run = self.scheduler.calculate_next_run(scheduled_call)

        self.scheduler._get_scheduled_call_groups()

        updated_scheduled_call = self.scheduled_call_collection.find_one({'_id': ObjectId(schedule_id)})
        self.assertEqual(next_next_run, updated_scheduled_call['next_run'])

    def test_scheduled_collision(self):
        call_request_scheduled = CallRequest(itinerary_call)
        schedule  = dateutils.format_iso8601_interval(datetime.timedelta(minutes=1),
                                                      datetime.datetime.now())
        schedule_id = self.scheduler.add(call_request_scheduled, schedule)

        call_request_in_progress = CallRequest(dummy_call)
        call_report_in_progress = CallReport.from_call_request(call_request_in_progress)
        call_report_in_progress.schedule_id = schedule_id

        # return a call report list out of the coordinator that has tasks from
        # this schedule in it
        # this will be cleaned up by the base class tearDown method
        mocked_coordinator = mock.Mock()
        mocked_call_reports = mock.Mock(return_value=[call_report_in_progress])
        mocked_coordinator.find_call_reports = mocked_call_reports
        dispatch_factory.coordinator = mock.Mock(return_value=mocked_coordinator)

        call_group_generator = self.scheduler._get_scheduled_call_groups()

        # call reports should have indicated a collision, in which we do not
        # run the scheduled call group again, indicated here by an "empty"
        # generator
        self.assertRaises(StopIteration, next, call_group_generator)

# query tests ------------------------------------------------------------------

class SchedulerQueryTests(SchedulerTests):

    def setUp(self):
        super(SchedulerQueryTests, self).setUp()
        self.scheduler._run_method = itinerary_call

    def test_get(self):
        call_request_1 = CallRequest(itinerary_call)
        schedule_id = self.scheduler.add(call_request_1, SCHEDULE_3_RUNS)
        self.assertFalse(schedule_id is None)
        schedule_report = self.scheduler.get(schedule_id)
        call_request_2 = schedule_report['call_request']
        schedule = schedule_report['schedule']
        self.assertFalse(schedule is None)
        self.assertFalse(call_request_2 is None)
        self.assertTrue(call_request_1.call == call_request_2.call)
        self.assertTrue(call_request_1.args == call_request_2.args)
        self.assertTrue(call_request_1.kwargs == call_request_2.kwargs)
        self.assertTrue(SCHEDULE_3_RUNS == schedule)

    def test_find_single_tag(self):
        tag = 'TAG'
        call_request_1 = CallRequest(itinerary_call)
        call_request_1.tags.append(tag)
        id_1 = self.scheduler.add(call_request_1, SCHEDULE_INDEFINITE_RUNS)
        call_list = self.scheduler.find(tag)
        self.assertTrue(len(call_list) == 1)

