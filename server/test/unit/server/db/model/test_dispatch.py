# -*- coding: utf-8 -*-
#
# Copyright ©2014 Red Hat, Inc.
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
Tests for the pulp.server.db.model.dispatch module.
"""
from datetime import datetime, timedelta
from uuid import uuid4
import pickle
import time
import unittest

import bson
import celery
from celery.schedules import schedule as CelerySchedule
from mongoengine import ValidationError
import mock

from pulp.common import dateutils, constants
from pulp.server.db.model.auth import User
from pulp.server.db.model.dispatch import TaskStatus, ScheduledCall, ScheduleEntry
from pulp.server.managers.factory import initialize


initialize()


class TestTaskStatus(unittest.TestCase):
    """
    Test the TaskStatus class.
    """
    def tearDown(self):
        """
        Remove the TaskStatus objects that were generated by these tests.
        """
        TaskStatus.objects().delete()

    def test___init__(self):
        """
        Test the __init__() method.
        """
        task_id = str(uuid4())
        worker_name = 'some_worker'
        tags = ['tag_1', 'tag_2']
        state = constants.CALL_ACCEPTED_STATE
        spawned_tasks = ['foo']
        error = {'error': 'some_error'}
        progress_report = {'what do we want?': 'progress!', 'when do we want it?': 'now!'}
        task_type = 'some.task'
        start_time = datetime.now()
        finish_time = start_time + timedelta(minutes=5)
        start_time = dateutils.format_iso8601_datetime(start_time)
        finish_time = dateutils.format_iso8601_datetime(finish_time)
        result = None

        ts = TaskStatus(
            task_id, worker_name, tags, state, spawned_tasks=spawned_tasks, error=error,
            progress_report=progress_report, task_type=task_type, start_time=start_time,
            finish_time=finish_time, result=result)

        self.assertEqual(ts.task_id, task_id)
        self.assertEqual(ts.worker_name, worker_name)
        self.assertEqual(ts.tags, tags)
        self.assertEqual(ts.state, state)
        self.assertEqual(ts.error, error)
        self.assertEqual(ts.spawned_tasks, spawned_tasks)
        self.assertEqual(ts.progress_report, progress_report)
        self.assertEqual(ts.task_type, task_type)
        self.assertEqual(ts.start_time, start_time)
        self.assertEqual(ts.finish_time, finish_time)
        self.assertEqual(ts.result, result)
        self.assertEqual(ts.traceback, None)
        self.assertEqual(ts.exception, None)

    def test___init___defaults(self):
        """
        Test the __init__() method with default values
        """
        task_id = str(uuid4())

        ts = TaskStatus(task_id)

        self.assertEqual(ts.task_id, task_id)
        self.assertEqual(ts.worker_name, None)
        self.assertEqual(ts.tags, [])
        self.assertEqual(ts.state, None)
        self.assertEqual(ts.result, None)
        self.assertEqual(ts.traceback, None)
        self.assertEqual(ts.start_time, None)
        self.assertEqual(ts.finish_time, None)
        self.assertEqual(ts.spawned_tasks, [])
        self.assertEqual(ts.error, None)
        self.assertEqual(ts.progress_report, {})
        self.assertEqual(ts.task_type, None)
        self.assertEqual(ts.exception, None)

    def test_task_id_validation(self):
        # Valid task_id
        valid_task_id = str(uuid4())
        TaskStatus(valid_task_id).save()

        # Invalid task_id
        invalid_task_ids = [4, {}, None, uuid4(), ('a', 'b'), object(), []]
        for invalid_task_id in invalid_task_ids:
            self.assertRaises(ValidationError, TaskStatus(invalid_task_id).save)

    def test_task_id_required(self):
        self.assertRaises(ValidationError, TaskStatus().save)
        self.assertRaises(ValidationError, TaskStatus(worker_name='worker_name').save)

    def test_worker_name_validation(self):
        # Valid worker_name
        task_id = str(uuid4())
        valid_worker_name = 'worker_name'
        TaskStatus(task_id=task_id, worker_name=valid_worker_name).save()

        # Invalid worker_name
        invalid_worker_names = [4, {}, uuid4(), ('a', 'b'), object(), []]
        for invalid_worker_name in invalid_worker_names:
            self.assertRaises(ValidationError, TaskStatus(task_id=task_id,
                                                          worker_name=invalid_worker_name).save)

    def test_tags_validation(self):
        # Valid tags
        task_id = str(uuid4())
        valid_tags = ['tag1', 'tag2']
        TaskStatus(task_id=task_id, tags=valid_tags).save()

        # Invalid tags
        invalid_tags = [4, {}, uuid4(), object(), 'tags', [1, 2]]
        for invalid_tag in invalid_tags:
            self.assertRaises(ValidationError, TaskStatus(task_id=task_id,
                                                          tags=invalid_tag).save)

    def test_state_validation(self):
        # Valid state
        valid_states = constants.CALL_STATES
        for valid_state in valid_states:
            TaskStatus(task_id=str(uuid4()), state=valid_state).save()

        # Invalid state
        invalid_states = [4, {}, uuid4(), object(), 'invalid_state', []]
        for invalid_state in invalid_states:
            self.assertRaises(ValidationError, TaskStatus(task_id=str(uuid4()),
                                                          state=invalid_state).save)

    def test_error_validation(self):
        # Valid error
        task_id = str(uuid4())
        valid_error = {'error': 'some error'}
        TaskStatus(task_id=task_id, error=valid_error).save()

        # Invalid error
        invalid_errors = [4, uuid4(), object(), 'tags', [1, 2]]
        for invalid_error in invalid_errors:
            self.assertRaises(ValidationError, TaskStatus(task_id=task_id,
                                                          error=invalid_error).save)

    def test_spawned_tasks_validation(self):
        # Valid spawned_tasks
        task_id = str(uuid4())
        valid_spawned_tasks = ['spawned1', 'spawned2']
        TaskStatus(task_id=task_id, spawned_tasks=valid_spawned_tasks).save()

        # Invalid spawned_tasks
        invalid_spawned_tasks = [4, uuid4(), object(), 'tags', [1, 2], {}]
        for invalid_spawned_task in invalid_spawned_tasks:
            self.assertRaises(ValidationError, TaskStatus(task_id=task_id,
                                                          spawned_tasks=invalid_spawned_task).save)

    def test_progress_report_validation(self):
        # Valid progress_report
        task_id = str(uuid4())
        valid_progress_report = {'progress': 'going good'}
        TaskStatus(task_id=task_id, progress_report=valid_progress_report).save()

        # Invalid progress_report
        invalid_progress_reports = [4, uuid4(), object(), 'tags', [1, 2], ()]
        for invalid_progress_report in invalid_progress_reports:
            self.assertRaises(ValidationError, TaskStatus(task_id=task_id,
                                                          progress_report=invalid_progress_report).save)

    def test_task_type_validation(self):
        # Valid task_type
        task_id = str(uuid4())
        valid_task_type = 'task_type'
        TaskStatus(task_id=task_id, task_type=valid_task_type).save()

        # Invalid task_type
        invalid_task_types = [4, {}, uuid4(), ('a', 'b'), object(), []]
        for invalid_task_type in invalid_task_types:
            self.assertRaises(ValidationError, TaskStatus(task_id=task_id,
                                                          task_type=invalid_task_type).save)

    def test_start_time_validation(self):
        # Valid start_time
        task_id = str(uuid4())
        valid_start_time = dateutils.format_iso8601_datetime(datetime.now())
        TaskStatus(task_id=task_id, start_time=valid_start_time).save()

        # Invalid start_time
        invalid_start_times = [4, {}, uuid4(), ('a', 'b'), object(), [], datetime.now()]
        for invalid_start_time in invalid_start_times:
            self.assertRaises(ValidationError, TaskStatus(task_id=task_id,
                                                          task_type=invalid_start_time).save)

    def test_finish_time_validation(self):
        # Valid finish_time
        task_id = str(uuid4())
        valid_finish_time = dateutils.format_iso8601_datetime(datetime.now())
        TaskStatus(task_id=task_id, finish_time=valid_finish_time).save()

        # Invalid finish_time
        invalid_finish_times = [4, {}, uuid4(), ('a', 'b'), object(), [], datetime.now()]
        for invalid_finish_time in invalid_finish_times:
            self.assertRaises(ValidationError, TaskStatus(task_id=task_id,
                                                          task_type=invalid_finish_time).save)

    def test_save_insert_defaults(self):
        """
        Test the save method with default arguments when the object is not already in the database.
        """
        task_id = str(uuid4())
        worker_name = 'some_worker'
        tags = ['tag_1', 'tag_2']
        state = constants.CALL_RUNNING_STATE
        spawned_tasks = ['foo']
        error = {'error': 'some_error'}
        progress_report = {'what do we want?': 'progress!', 'when do we want it?': 'now!'}
        task_type = 'some.task'
        start_time = datetime.now()
        finish_time = start_time + timedelta(minutes=5)
        start_time = dateutils.format_iso8601_datetime(start_time)
        finish_time = dateutils.format_iso8601_datetime(finish_time)
        result = None
        ts = TaskStatus(
            task_id, worker_name, tags, state, spawned_tasks=spawned_tasks, error=error,
            progress_report=progress_report, task_type=task_type, start_time=start_time,
            finish_time=finish_time, result=result)

        # This should cause ts to be in the database
        ts.save()

        ts = TaskStatus.objects()
        # There should only be one TaskStatus in the db
        self.assertEqual(len(ts), 1)
        ts = ts[0]
        # Make sure all the attributes are correct
        self.assertEqual(ts['task_id'], task_id)
        self.assertEqual(ts['worker_name'], worker_name)
        self.assertEqual(ts['tags'], tags)
        self.assertEqual(ts['state'], state)
        self.assertEqual(ts['error'], error)
        self.assertEqual(ts['spawned_tasks'], spawned_tasks)
        self.assertEqual(ts['progress_report'], progress_report)
        self.assertEqual(ts['task_type'], task_type)
        self.assertEqual(ts['start_time'], start_time)
        self.assertEqual(ts['finish_time'], finish_time)
        self.assertEqual(ts['result'], result)
        # These are always None
        self.assertEqual(ts['traceback'], None)
        self.assertEqual(ts['exception'], None)

    def test_save_insert_with_set_on_insert(self):
        """
        Test the save method with set on insert arguments when the object is not already in the
        database.
        """
        task_id = str(uuid4())
        worker_name = 'some_worker'
        tags = ['tag_1', 'tag_2']
        state = constants.CALL_RUNNING_STATE
        spawned_tasks = ['foo']
        error = {'error': 'some_error'}
        progress_report = {'what do we want?': 'progress!', 'when do we want it?': 'now!'}
        task_type = 'some.task'
        start_time = datetime.now()
        finish_time = start_time + timedelta(minutes=5)
        start_time = dateutils.format_iso8601_datetime(start_time)
        finish_time = dateutils.format_iso8601_datetime(finish_time)
        result = None
        ts = TaskStatus(
            task_id, worker_name, tags, state, spawned_tasks=spawned_tasks, error=error,
            progress_report=progress_report, task_type=task_type, start_time=start_time,
            finish_time=finish_time, result=result)

        # This should cause ts to be in the database
        ts.save_with_set_on_insert(fields_to_set_on_insert=['state', 'start_time'])

        ts = TaskStatus.objects()
        # There should only be one TaskStatus in the db
        self.assertEqual(len(ts), 1)
        ts = ts[0]
        # Make sure all the attributes are correct
        self.assertEqual(ts['task_id'], task_id)
        self.assertEqual(ts['worker_name'], worker_name)
        self.assertEqual(ts['tags'], tags)
        self.assertEqual(ts['state'], state)
        self.assertEqual(ts['error'], error)
        self.assertEqual(ts['spawned_tasks'], spawned_tasks)
        self.assertEqual(ts['progress_report'], progress_report)
        self.assertEqual(ts['task_type'], task_type)
        self.assertEqual(ts['start_time'], start_time)
        self.assertEqual(ts['finish_time'], finish_time)
        self.assertEqual(ts['result'], result)
        # These are always None
        self.assertEqual(ts['traceback'], None)
        self.assertEqual(ts['exception'], None)

    def test_save_update_defaults(self):
        """
        Test the save method with default arguments when the object is already in the database.
        """
        task_id = str(uuid4())
        worker_name = 'worker_name'
        tags = ['tag_1', 'tag_2']
        state = constants.CALL_ACCEPTED_STATE
        spawned_tasks = ['foo']
        error = {'error': 'some_error'}
        progress_report = {'what do we want?': 'progress!', 'when do we want it?': 'now!'}
        task_type = 'some.task'
        start_time = datetime.now()
        finish_time = start_time + timedelta(minutes=5)
        start_time = dateutils.format_iso8601_datetime(start_time)
        finish_time = dateutils.format_iso8601_datetime(finish_time)
        result = None
        ts = TaskStatus(
            task_id, worker_name, tags, state, spawned_tasks=spawned_tasks, error=error,
            progress_report=progress_report, task_type=task_type, start_time=start_time,
            finish_time=finish_time, result=result)
        # Let's go ahead and insert the object
        ts.save()
        # Now let's alter it a bit, and make sure the alteration makes it to the DB correctly.
        new_state = constants.CALL_RUNNING_STATE
        ts.state = new_state

        # This should update ts in the database
        ts.save()

        ts = TaskStatus.objects()
        # There should only be one TaskStatus in the db
        self.assertEqual(len(ts), 1)
        ts = ts[0]
        # Make sure all the attributes are correct
        self.assertEqual(ts['task_id'], task_id)
        self.assertEqual(ts['worker_name'], worker_name)
        self.assertEqual(ts['tags'], tags)
        # The state should have been updated
        self.assertEqual(ts['state'], new_state)
        self.assertEqual(ts['error'], error)
        self.assertEqual(ts['spawned_tasks'], spawned_tasks)
        self.assertEqual(ts['progress_report'], progress_report)
        self.assertEqual(ts['task_type'], task_type)
        self.assertEqual(ts['start_time'], start_time)
        self.assertEqual(ts['finish_time'], finish_time)
        self.assertEqual(ts['result'], result)
        # These are always None
        self.assertEqual(ts['traceback'], None)
        self.assertEqual(ts['exception'], None)

    def test_save_update_with_set_on_insert(self):
        """
        Test the save method with set on insert arguments when the object is already in the
        database.
        """
        task_id = str(uuid4())
        worker_name = 'worker_name'
        tags = ['tag_1', 'tag_2']
        state = constants.CALL_ACCEPTED_STATE
        spawned_tasks = ['foo']
        error = {'error': 'some_error'}
        progress_report = {'what do we want?': 'progress!', 'when do we want it?': 'now!'}
        task_type = 'some.task'
        old_start_time = start_time = datetime.now()
        finish_time = start_time + timedelta(minutes=5)
        start_time = dateutils.format_iso8601_datetime(start_time)
        finish_time = dateutils.format_iso8601_datetime(finish_time)
        result = None
        ts = TaskStatus(
            task_id, worker_name, tags, state, spawned_tasks=spawned_tasks, error=error,
            progress_report=progress_report, task_type=task_type, start_time=start_time,
            finish_time=finish_time, result=result)
        # Put the object in the database, and then change some of it settings.
        ts.save()
        new_worker_name = 'a different_worker'
        new_state = constants.CALL_SUSPENDED_STATE
        new_start_time = old_start_time + timedelta(minutes=10)
        new_start_time = dateutils.format_iso8601_datetime(new_start_time)
        ts.worker_name = new_worker_name
        ts.state = new_state
        ts.start_time = new_start_time

        # This should update the worker_name on ts in the database, but should not update the state
        # or start_time
        ts.save_with_set_on_insert(fields_to_set_on_insert=['state', 'start_time'])

        ts = TaskStatus.objects()
        # There should only be one TaskStatus in the db
        self.assertEqual(len(ts), 1)
        ts = ts[0]
        # Make sure all the attributes are correct
        self.assertEqual(ts['task_id'], task_id)
        # Queue should have been updated
        self.assertEqual(ts['worker_name'], new_worker_name)
        self.assertEqual(ts['tags'], tags)
        # state should not have been updated
        self.assertEqual(ts['state'], state)
        self.assertEqual(ts['error'], error)
        self.assertEqual(ts['spawned_tasks'], spawned_tasks)
        self.assertEqual(ts['progress_report'], progress_report)
        self.assertEqual(ts['task_type'], task_type)
        # start_time should not have been updated
        self.assertEqual(ts['start_time'], start_time)
        self.assertEqual(ts['finish_time'], finish_time)
        self.assertEqual(ts['result'], result)
        # These are always None
        self.assertEqual(ts['traceback'], None)
        self.assertEqual(ts['exception'], None)


class TestScheduledCallInit(unittest.TestCase):
    def test_new(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        # make sure the call generates its own object ID
        self.assertTrue(len(call.id) > 0)
        self.assertTrue(isinstance(call._id, bson.ObjectId))

    def test_pass_in_task_name(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        self.assertEqual(call.task, 'pulp.tasks.dosomething')

    def test_set_task_name(self):
        task = mock.MagicMock()
        task.name = 'pulp.tasks.dosomething'

        call = ScheduledCall('PT1M', task)

        # make sure it saves the task's name
        self.assertEqual(call.task, task.name)

    def test_pass_in_schedule(self):
        schedule = pickle.dumps(CelerySchedule(60))

        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething', schedule=schedule)

        self.assertEqual(call.schedule, schedule)

    def test_create_schedule(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        schedule = pickle.loads(call.schedule)

        self.assertTrue(isinstance(schedule, CelerySchedule))
        self.assertEqual(schedule.run_every, timedelta(minutes=1))

    def test_pass_in_principal(self):
        principal = User('me', 'letmein')
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething', principal=principal)

        self.assertEqual(call.principal, principal)

    def test_create_principal(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        # See PrincipalManager.get_principal(). It returns either a User or
        # a dict. Not my idea.
        self.assertTrue(isinstance(call.principal, (User, dict)))

    def test_no_first_run(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        first_run = dateutils.parse_iso8601_datetime(call.first_run)

        # generously make sure the calculated first_run is within 1 second of now
        now = datetime.utcnow().replace(tzinfo=dateutils.utc_tz())
        self.assertTrue(abs(now - first_run) < timedelta(seconds=1))

    def test_first_run_datetime(self):
        first_run = datetime.utcnow().replace(tzinfo=dateutils.utc_tz()) + timedelta(days=1)

        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething', first_run=first_run)

        # make sure it is an ISO8601 string with the correct value
        self.assertTrue(isinstance(call.first_run, basestring))
        self.assertEqual(dateutils.format_iso8601_datetime(first_run), call.first_run)

    def test_first_run_string(self):
        first_run = dateutils.format_iso8601_datetime(
            datetime.utcnow().replace(tzinfo=dateutils.utc_tz()) + timedelta(days=1))

        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething', first_run=first_run)

        self.assertEqual(first_run, call.first_run)

    def test_remaining_runs_none(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        self.assertTrue(call.remaining_runs is None)

    def test_remaining_runs_in_string(self):
        call = ScheduledCall('R3/PT1M', 'pulp.tasks.dosomething')

        self.assertEqual(call.remaining_runs, 3)

    def test_remaining_runs_passed_int(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething', remaining_runs=2)

        self.assertEqual(call.remaining_runs, 2)

    def test_next_run_ignored(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething', next_run='foo')

        self.assertTrue(call.next_run != 'foo')

    @mock.patch.object(ScheduledCall, 'calculate_next_run')
    def test_next_run_calculated(self, mock_calc):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething', next_run='foo')

        self.assertEqual(call.next_run, mock_calc.return_value)
        mock_calc.assert_called_once_with()


class TestScheduledCallFromDB(unittest.TestCase):
    def setUp(self):
        super(TestScheduledCallFromDB, self).setUp()
        self.schedule = bson.SON(SCHEDULE)

    def test_returns_instance(self):
        call = ScheduledCall.from_db(self.schedule)

        self.assertTrue(isinstance(call, ScheduledCall))

    def test_preserves_id(self):
        call = ScheduledCall.from_db(self.schedule)

        self.assertEqual(call.id, '529f4bd93de3a31d0ec77338')


class TestScheduledCallAsEntry(unittest.TestCase):
    def setUp(self):
        super(TestScheduledCallAsEntry, self).setUp()
        self.schedule = bson.SON(SCHEDULE)

    def test_returns_instance(self):
        call = ScheduledCall.from_db(self.schedule)

        entry = call.as_schedule_entry()

        self.assertTrue(isinstance(entry, celery.beat.ScheduleEntry))

    def test_values(self):
        call = ScheduledCall.from_db(self.schedule)

        entry = call.as_schedule_entry()

        self.assertEqual(entry._scheduled_call, call)
        self.assertTrue(isinstance(entry.schedule, CelerySchedule))
        self.assertEqual(entry.args, call.args)
        self.assertEqual(entry.kwargs, call.kwargs)
        self.assertEqual(entry.name, call.name)
        self.assertEqual(entry.task, call.task)
        self.assertEqual(entry.options, call.options)
        self.assertEqual(entry.last_run_at, dateutils.parse_iso8601_datetime(call.last_run_at))
        self.assertFalse(entry.schedule.relative)

    def test_no_last_run(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        entry = call.as_schedule_entry()

        # celery actually calculates it, so we don't need to test the value
        self.assertTrue(isinstance(entry.last_run_at, datetime))


class TestScheduledCallAsDict(unittest.TestCase):
    def test_returns_dict(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        self.assertTrue(isinstance(call.as_dict(), dict))

    def test_values(self):
        schedule = bson.SON(SCHEDULE)
        call = ScheduledCall.from_db(schedule)

        result = call.as_dict()

        self.assertEqual(result['_id'], call.id)
        for k, v in SCHEDULE.items():
            self.assertEqual(v, result[k])
        self.assertTrue('next_run' in result)


class TestScheduledCallForDisplay(unittest.TestCase):
    def test_returns_dict(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        self.assertTrue(isinstance(call.for_display(), dict))

    def test_values(self):
        schedule = bson.SON(SCHEDULE)
        call = ScheduledCall.from_db(schedule)

        as_dict = call.as_dict()
        result = call.for_display()

        for k, v in result.items():
            if k not in ['schedule', 'iso_schedule']:
                self.assertEqual(v, as_dict[k])
        self.assertEqual(result['schedule'], as_dict['iso_schedule'])


@mock.patch('pulp.server.db.model.base.Model.get_collection')
class TestScheduledCallSave(unittest.TestCase):
    def test_existing(self, mock_get_collection):
        mock_update = mock_get_collection.return_value.update
        fake_id = bson.ObjectId()
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething', id=fake_id)

        call.save()

        expected = call.as_dict()
        del expected['_id']
        mock_update.assert_called_once_with({'_id': fake_id}, expected)

    def test_new(self, mock_get_collection):
        mock_insert = mock_get_collection.return_value.insert
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        call.save()

        expected = call.as_dict()
        expected['_id'] = bson.ObjectId(expected['_id'])
        mock_insert.assert_called_once_with(expected, safe=True)
        self.assertFalse(call._new)


class TestScheduledCallCalculateTimes(unittest.TestCase):
    def test_now(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        now = call._calculate_times()[0]

        # make sure this gives us a timestamp that reasonably represents "now"
        self.assertTrue(time.time() - now < 1)

    def test_first_run_now(self):
        call = ScheduledCall('PT1M', 'pulp.tasks.dosomething')

        first_run_s = call._calculate_times()[1]

        # make sure this gives us a timestamp that reasonably represents "now"
        self.assertTrue(time.time() - first_run_s < 1)

    def test_first_run_scheduled(self):
        call = ScheduledCall('2014-01-03T10:15Z/PT1H', 'pulp.tasks.dosomething')

        first_run_s = call._calculate_times()[1]

        # make sure this gives us a timestamp for the date and time
        # specified above
        self.assertEqual(first_run_s, 1388744100)

    def test_first_run_saved(self):
        """
        Test that when the first run is passed in from historical data.
        """
        call = ScheduledCall('PT1H', 'pulp.tasks.dosomething', first_run='2014-01-03T10:15Z')

        first_run_s = call._calculate_times()[1]

        # make sure this gives us a timestamp for the date and time
        # specified above
        self.assertEqual(first_run_s, 1388744100)

    def test_since_first(self):
        call = ScheduledCall('2014-01-03T10:15Z/PT1H', 'pulp.tasks.dosomething')

        since_first = call._calculate_times()[2]
        now = time.time()

        self.assertTrue(since_first + 1388744100 - now < 1)

    def test_run_every(self):
        call = ScheduledCall('2014-01-03T10:15Z/PT1H', 'pulp.tasks.dosomething')

        run_every_s = call._calculate_times()[3]

        # 1 hour, as specified in the ISO8601 string above
        self.assertEqual(run_every_s, 3600)

    def test_last_scheduled_run_no_first_run(self):
        call = ScheduledCall('PT1H', 'pulp.tasks.dosomething')

        last_scheduled_run_s = call._calculate_times()[4]
        first_run_s = call._calculate_times()[1]

        self.assertEqual(last_scheduled_run_s, first_run_s)

    @mock.patch('time.time')
    def test_last_scheduled_run_with_first_run(self, mock_time):
        # specify a start time and current time such that we know the difference
        mock_time.return_value = 1389307330.966561
        call = ScheduledCall('2014-01-09T17:15Z/PT1H', 'pulp.tasks.dosomething')

        last_scheduled_run_s = call._calculate_times()[4]

        self.assertEqual(last_scheduled_run_s, 1389305700)

    @mock.patch('time.time')
    def test_expected_runs_positive(self, mock_time):
        # specify a start time and current time such that we know the difference
        mock_time.return_value = 1389307330.966561
        call = ScheduledCall('2014-01-09T17:15Z/PT1H', 'pulp.tasks.dosomething')

        expected_runs = call._calculate_times()[5]

        # we know that it's been more than 5 hours since the first scheduled run
        self.assertEqual(expected_runs, 5)

    @mock.patch('time.time')
    def test_expected_runs_future(self, mock_time):
        # specify a start time and current time such that the start appears to
        # be in the future
        mock_time.return_value = 1389307330.966561
        call = ScheduledCall('2014-01-19T17:15Z/PT1H', 'pulp.tasks.dosomething')

        expected_runs = call._calculate_times()[5]

        # the first run is scheduled in the future (relative to the mock time),
        # so there should not be any runs.
        self.assertEqual(expected_runs, 0)

    def test_expected_runs_zero(self):
        call = ScheduledCall('PT1H', 'pulp.tasks.dosomething')

        expected_runs = call._calculate_times()[5]

        self.assertEqual(expected_runs, 0)


class TestScheduledCallCalculateNextRun(unittest.TestCase):
    @mock.patch('time.time')
    def test_future(self, mock_time):
        mock_time.return_value = 1389307330.966561
        call = ScheduledCall('2014-01-19T17:15Z/PT1H', 'pulp.tasks.dosomething')

        next_run = call.calculate_next_run()

        # make sure the next run is equal to the specified first run.
        # don't want to compare a generated ISO8601 string directly, because there
        # could be subtle variations that are valid but break string equality.
        self.assertEqual(dateutils.parse_iso8601_interval(call.iso_schedule)[1],
                         dateutils.parse_iso8601_datetime(next_run))

    def test_now(self):
        call = ScheduledCall('PT1H', 'pulp.tasks.dosomething')

        now = datetime.utcnow().replace(tzinfo=dateutils.utc_tz())
        next_run = dateutils.parse_iso8601_datetime(call.calculate_next_run())

        self.assertTrue(next_run - now < timedelta(seconds=1))

    @mock.patch('time.time')
    def test_with_past_runs(self, mock_time):
        # setup an hourly call that first ran not quite 2 hours ago, ran again
        # less than one hour ago, and should be scheduled to run at the end of
        # this hour
        mock_time.return_value = 1389389758.547976
        call = ScheduledCall('2014-01-10T20:00Z/PT1H', 'pulp.tasks.dosomething',
                             total_run_count=2, last_run_at='2014-01-10T21:00Z')

        next_run = call.calculate_next_run()

        self.assertEqual(dateutils.parse_iso8601_datetime('2014-01-10T22:00Z'),
                         dateutils.parse_iso8601_datetime(next_run))

    @mock.patch('time.time')
    def test_with_months_duration(self, mock_time):
        """
        Test calculating the next run when the interval is a Duration object and uses months
        """
        last_runs = ('2015-01-01T10:00Z', '2015-02-01T10:00Z', '2015-03-01T10:00Z', '2015-04-01T10:00Z')
        expected_next_runs = ('2015-02-01T10:00Z', '2015-03-01T10:00Z', '2015-04-01T10:00Z', '2015-05-01T10:00Z')
        times = (
            1422784799.0,  # Just before 2015-02-01T10:00Z UTC
            1425203999.0,  # Just before 2015-03-01T10:00Z UTC
            1427882399.0,  # Just before 2015-04-01T10:00Z UTC
            1430474399.0,  # Just before 2015-05-01T10:00Z UTC
        )

        for last_run, current_time, expected_next_run in zip(last_runs, times, expected_next_runs):
            mock_time.return_value = current_time
            call = ScheduledCall('2014-12-01T10:00Z/P1M', 'pulp.tasks.dosomething',
                                 total_run_count=2, last_run_at=last_run)
            next_run = call.calculate_next_run()

            self.assertEqual(dateutils.parse_iso8601_datetime(expected_next_run),
                             dateutils.parse_iso8601_datetime(next_run))

    @mock.patch('time.time')
    def test_with_years_duration(self, mock_time):
        """
        Test calculating the next run when the interval is a Duration object and uses years
        """
        last_runs = ('2015-01-01T10:00Z', '2016-01-01T10:00Z', '2017-01-01T10:00Z', '2018-01-01T10:00Z')
        expected_next_runs = ('2016-01-01T10:00Z', '2017-01-01T10:00Z', '2018-01-01T10:00Z', '2019-01-01T10:00Z')
        times = (
            1451642000.0,  # Just before 2016-01-01T10:00Z UTC
            1483264000.0,  # Just before 2017-01-01T10:00Z UTC
            1514800000.0,  # Just before 2018-01-01T10:00Z UTC
            1546336000.0,  # Just before 2019-01-01T10:00Z UTC
        )

        for last_run, current_time, expected_next_run in zip(last_runs, times, expected_next_runs):
            mock_time.return_value = current_time
            call = ScheduledCall('2014-01-01T10:00Z/P1M', 'pulp.tasks.dosomething',
                                 total_run_count=2, last_run_at=last_run)
            next_run = call.calculate_next_run()

            self.assertEqual(dateutils.parse_iso8601_datetime(expected_next_run),
                             dateutils.parse_iso8601_datetime(next_run))


class TestScheduleEntryInit(unittest.TestCase):
    def test_captures_scheduled_call(self):
        call = ScheduledCall('2014-01-19T17:15Z/PT1H', 'pulp.tasks.dosomething')
        entry = call.as_schedule_entry()

        self.assertTrue(hasattr(entry, '_scheduled_call'))
        self.assertTrue(entry._scheduled_call is call)


@mock.patch.object(ScheduledCall, 'save')
class TestScheduleEntryNextInstance(unittest.TestCase):
    def setUp(self):
        super(TestScheduleEntryNextInstance, self).setUp()
        self.call = ScheduledCall('2014-01-19T17:15Z/PT1H', 'pulp.tasks.dosomething',
                                  remaining_runs=5)
        self.entry = self.call.as_schedule_entry()

    def test_increments_last_run(self, mock_save):
        next_entry = next(self.entry)
        now = datetime.utcnow().replace(tzinfo=dateutils.utc_tz())

        self.assertTrue(now - next_entry.last_run_at < timedelta(seconds=1))

    def test_increments_run_count(self, mock_save):
        next_entry = next(self.entry)

        self.assertEqual(self.entry.total_run_count + 1, next_entry.total_run_count)

    def test_decrements_remaining_runs(self, mock_save):
        remaining = self.call.remaining_runs

        next(self.entry)

        self.assertEqual(remaining - 1, self.call.remaining_runs)

    def test_disables_for_remaining_runs(self, mock_save):
        self.call.remaining_runs = 1
        # just verify that we have the correct starting state
        self.assertTrue(self.call.enabled)

        next(self.entry)

        # call should have been disabled because the remaining_runs hit 0
        self.assertFalse(self.call.enabled)

    def test_calls_save(self, mock_save):
        next(self.entry)

        mock_save.assert_called_once_with()

    def test_returns_entry(self, mock_save):
        next_entry = next(self.entry)

        self.assertTrue(isinstance(next_entry, ScheduleEntry))
        self.assertEqual(self.entry.name, next_entry.name)
        self.assertFalse(self.entry is next_entry)


class TestScheduleEntryIsDue(unittest.TestCase):
    def setUp(self):
        super(TestScheduleEntryIsDue, self).setUp()
        self.call = ScheduledCall('2014-01-19T17:15Z/PT1H', 'pulp.tasks.dosomething',
                                  remaining_runs=5)
        self.entry = self.call.as_schedule_entry()

    @mock.patch('time.time')
    def test_first_run_future(self, mock_time):
        mock_time.return_value = 1389307330

        is_due, seconds = self.entry.is_due()

        self.assertFalse(is_due)
        self.assertEqual(seconds, 844370)

    def test_no_runs(self):
        call = ScheduledCall('PT1H', 'pulp.tasks.dosomething')
        entry = call.as_schedule_entry()

        is_due, seconds = entry.is_due()

        self.assertTrue(is_due)
        # make sure this is very close to one hour
        self.assertTrue(3600 - seconds < 1)

    @mock.patch('time.time')
    def test_past_runs_due(self, mock_time):
        mock_time.return_value = 1389389758  # 2014-01-10T21:35:58
        # This call did not run at the top of the hour, so it is overdue and should
        # run now. Its next run will be back on the normal hourly schedule, at
        # the top of the next hour.
        call = ScheduledCall('2014-01-10T20:00Z/PT1H', 'pulp.tasks.dosomething',
                             last_run_at='2014-01-10T20:00Z', total_run_count=1)
        entry = call.as_schedule_entry()

        is_due, seconds = entry.is_due()

        self.assertTrue(is_due)
        # this was hand-calculated as the remaining time until the next hourly run
        self.assertEqual(seconds, 1442)

    @mock.patch('time.time')
    def test_past_runs_not_due(self, mock_time):
        mock_time.return_value = 1389389758  # 2014-01-10T21:35:58
        # This call ran at the top of the hour, so it does not need to run again
        # until the top of the next hour.
        call = ScheduledCall('2014-01-10T20:00Z/PT1H', 'pulp.tasks.dosomething',
                             last_run_at='2014-01-10T21:00Z', total_run_count=2)
        entry = call.as_schedule_entry()

        is_due, seconds = entry.is_due()

        self.assertFalse(is_due)
        # this was hand-calculated as the remaining time until the next hourly run
        self.assertEqual(seconds, 1442)


SCHEDULE = {
    u'_id': u'529f4bd93de3a31d0ec77338',
    u'args': [u'demo1', u'puppet_distributor'],
    u'consecutive_failures': 0,
    u'enabled': True,
    u'failure_threshold': 2,
    u'first_run': u'2013-12-04T15:35:53Z',
    u'iso_schedule': u'PT1M',
    u'kwargs': {u'overrides': {}},
    u'last_run_at': u'2013-12-17T00:35:53Z',
    u'last_updated': 1387218569.811224,
    u'principal': u"(dp0\nV_id\np1\nccopy_reg\n_reconstructor\np2\n(cbson.objectid\nObjectId\np3\nc__builtin__\nobject\np4\nNtp5\nRp6\nS'R \\xab\\x06\\xe1\\x9a\\x00\\x10\\xe1i\\x05\\x89'\np7\nbsVname\np8\nVadmin\np9\nsVroles\np10\n(lp11\nVsuper-users\np12\nasV_ns\np13\nVusers\np14\nsVlogin\np15\nVadmin\np16\nsVpassword\np17\nVV76Yol1XYgM=,S/G6o5UyMrn0xAwbQCqFcrXnfXTh84RWhunanCDkSCo=\np18\nsVid\np19\nV5220ab06e19a0010e1690589\np20\ns.",
    u'remaining_runs': None,
    u'resource': u'pulp:distributor:demo:puppet_distributor',
    u'schedule': u"ccopy_reg\n_reconstructor\np0\n(ccelery.schedules\nschedule\np1\nc__builtin__\nobject\np2\nNtp3\nRp4\n(dp5\nS'relative'\np6\nI00\nsS'nowfun'\np7\nNsS'run_every'\np8\ncdatetime\ntimedelta\np9\n(I0\nI60\nI0\ntp10\nRp11\nsb.",
    u'task': u'pulp.server.tasks.repository.publish',
    u'total_run_count': 1087,
}
