from datetime import datetime, timedelta
import time
import unittest

from celery.beat import ScheduleEntry
import mock

from pulp.server.async import scheduler
from pulp.server.async.celery_instance import celery as app
from pulp.server.async.celery_instance import RESOURCE_MANAGER_QUEUE
from pulp.server.db.model import dispatch, resources
from pulp.server.db.model.criteria import Criteria
from pulp.server.managers.factory import initialize


initialize()


class TestFailureWatcherLen(unittest.TestCase):
    def test_empty(self):
        watcher = scheduler.FailureWatcher()

        self.assertEqual(len(watcher), 0)

    def test_increments(self):
        watcher = scheduler.FailureWatcher()

        for i in range(1, 10):
            watcher.add('task-%d' % i, 'schedule-%d' % i, False)
            self.assertEqual(len(watcher), i)


class TestFailureWatcherTrim(unittest.TestCase):
    def test_removes_old(self):
        watcher = scheduler.FailureWatcher()
        watcher._watches['some_task'] = watcher.WatchedTask(int(time.time()) - watcher.ttl - 1,
                                                            'some_schedule', False)

        watcher.trim()

        self.assertEqual(len(watcher), 0)

    def test_keeps_new(self):
        watcher = scheduler.FailureWatcher()
        watcher.add('some_task', 'some_schedule', False)

        watcher.trim()

        self.assertEqual(len(watcher), 1)


class TestFailureWatcherAdd(unittest.TestCase):
    def test_can_retrieve(self):
        watcher = scheduler.FailureWatcher()
        watcher.add('some_task', 'some_schedule', False)

        schedule_id, has_failure = watcher.pop('some_task')

        self.assertEqual(schedule_id, 'some_schedule')
        self.assertFalse(has_failure)

    def test_time(self):
        watcher = scheduler.FailureWatcher()
        watcher.add('some_task', 'some_schedule', False)

        watched_task = watcher._watches['some_task']

        self.assertTrue(time.time() - watched_task.timestamp < 1)


class TestFailureWatcherPop(unittest.TestCase):
    def test_can_retrieve(self):
        watcher = scheduler.FailureWatcher()
        watcher.add('some_task', 'some_schedule', False)

        schedule_id, has_failure = watcher.pop('some_task')

        self.assertEqual(schedule_id, 'some_schedule')
        self.assertFalse(has_failure)

    def test_removes(self):
        watcher = scheduler.FailureWatcher()
        watcher.add('some_task', 'some_schedule', False)

        schedule_id, has_failure = watcher.pop('some_task')

        self.assertEqual(len(watcher), 0)


class TestEventMonitorInit(unittest.TestCase):
    @mock.patch('threading.Thread.__init__')
    def test_event_monitor__init__(self, mock_thread__init__):
        failure_watcher = scheduler.FailureWatcher()
        event_monitor = scheduler.EventMonitor(failure_watcher)
        mock_thread__init__.assert_called_once_with()
        self.assertTrue(failure_watcher is event_monitor._failure_watcher)


class TestEventMonitorEvents(unittest.TestCase):
    def setUp(self):
        self.failure_watcher = scheduler.FailureWatcher()
        self.event_monitor = scheduler.EventMonitor(self.failure_watcher)

    @mock.patch('pulp.server.async.scheduler.app.events.Receiver')
    def test_handlers_declared(self, mock_receiver):
        self.event_monitor.monitor_events()

        self.assertEqual(mock_receiver.call_count, 1)
        self.assertEqual(mock_receiver.return_value.capture.call_count, 1)
        handlers = mock_receiver.call_args[1]['handlers']

        self.assertTrue('task-failed' in handlers)
        self.assertTrue('task-succeeded' in handlers)
        self.assertTrue('worker-heartbeat' in handlers)
        self.assertTrue('worker-offline' in handlers)

    @mock.patch('pulp.server.async.scheduler.app.connection')
    @mock.patch('pulp.server.async.scheduler.app.events.Receiver')
    def test_connection_passed(self, mock_receiver, mock_connection):
        self.event_monitor.monitor_events()
        self.assertTrue(mock_receiver.call_args[0][0] is
                        mock_connection.return_value.__enter__.return_value)
        capture = mock_receiver.return_value.capture
        capture.assert_called_once_with(limit=None, timeout=None, wakeup=True)


class TestHandleSucceededTask(unittest.TestCase):
    def setUp(self):
        self.event = {'uuid': 'task_1'}

    @mock.patch('celery.result.AsyncResult')
    def test_not_found(self, mock_result):
        watcher = scheduler.FailureWatcher()

        watcher.handle_succeeded_task(self.event)

        # did not try to fetch a result
        self.assertEqual(mock_result.call_count, 0)

    @mock.patch.object(scheduler.FailureWatcher, 'add')
    @mock.patch('pulp.server.async.scheduler.AsyncResult')
    def test_rewatch(self, mock_result, mock_add):
        """
        if a task's return value is an AsyncResult, that means it queued another
        task that we should now watch.
        """
        mock_result.return_value.result.id = 'task_1'

        # this seems to be the only way to mock isinstance
        scheduler.isinstance = mock.MagicMock(return_value=True)
        try:
            watcher = scheduler.FailureWatcher()
            watcher._watches['task_1'] = watcher.WatchedTask(int(time.time()), 'some_schedule', False)

            watcher.handle_succeeded_task(self.event)

            mock_add.assert_called_once_with('task_1', 'some_schedule', False)
        finally:
            del scheduler.isinstance

    @mock.patch('pulp.server.managers.schedule.utils.reset_failure_count')
    @mock.patch('pulp.server.async.scheduler.AsyncResult')
    def test_has_failure(self, mock_result, mock_reset):
        watcher = scheduler.FailureWatcher()
        watcher.add('task_1', 'some_schedule', True)

        # this seems to be the only way to mock isinstance
        scheduler.isinstance = mock.MagicMock(return_value=False)
        try:
            watcher.handle_succeeded_task(self.event)

            mock_reset.assert_called_once_with('some_schedule')
        finally:
            del scheduler.isinstance


class TestHandleFailedTask(unittest.TestCase):
    def setUp(self):
        self.event = {'uuid': 'task_1'}

    @mock.patch('pulp.server.managers.schedule.utils.increment_failure_count')
    def test_not_found(self, mock_increment):
        watcher = scheduler.FailureWatcher()

        watcher.handle_failed_task(self.event)

        # did not try to fetch a result
        self.assertEqual(mock_increment.call_count, 0)

    @mock.patch('pulp.server.managers.schedule.utils.increment_failure_count')
    def test_found(self, mock_increment):
        watcher = scheduler.FailureWatcher()
        watcher.add('task_1', 'some_schedule', True)

        watcher.handle_failed_task(self.event)

        mock_increment.assert_called_once_with('some_schedule')


class TestSchedulerInit(unittest.TestCase):
    @mock.patch.object(scheduler.Scheduler, 'setup_schedule', new=mock.MagicMock())
    @mock.patch('celery.beat.Scheduler.__init__')
    @mock.patch.object(scheduler.Scheduler, 'spawn_pulp_monitor_threads')
    def test__init__(self, mock_spawn_pulp_monitor_threads, mock_base_init):
        arg1 = mock.Mock()
        arg2 = mock.Mock()
        kwarg1 = mock.Mock()
        kwarg2 = mock.Mock()

        my_scheduler = scheduler.Scheduler(arg1, arg2, kwarg1=kwarg1, kwarg2=kwarg2)

        self.assertTrue(my_scheduler._schedule is None)
        self.assertTrue(isinstance(my_scheduler._failure_watcher, scheduler.FailureWatcher))
        self.assertTrue(my_scheduler._loaded_from_db_count == 0)
        self.assertTrue(not mock_spawn_pulp_monitor_threads.called)
        self.assertTrue(scheduler.Scheduler._mongo_initialized is False)
        mock_base_init.assert_called_once_with(arg1, arg2, app=app, kwarg1=kwarg1, kwarg2=kwarg2)

    @mock.patch('celery.beat.Scheduler.__init__', new=mock.Mock())
    @mock.patch.object(scheduler.Scheduler, 'spawn_pulp_monitor_threads')
    @mock.patch('pulp.server.async.scheduler.EventMonitor')
    def test__init__lazy_is_True(self, mock_event_monitor, mock_spawn_pulp_monitor_threads):
        mock_app = mock.Mock()
        scheduler.Scheduler(mock_app, lazy=True)
        self.assertTrue(not mock_spawn_pulp_monitor_threads.called)

    @mock.patch('celery.beat.Scheduler.__init__', new=mock.Mock())
    @mock.patch.object(scheduler.Scheduler, 'spawn_pulp_monitor_threads')
    @mock.patch('pulp.server.async.scheduler.EventMonitor')
    def test__init__lazy_is_False(self, mock_event_monitor, mock_spawn_pulp_monitor_threads):
        mock_app = mock.Mock()
        scheduler.Scheduler(mock_app, lazy=False)
        self.assertTrue(mock_spawn_pulp_monitor_threads.called)


class TestSchedulerSpawnPulpMonitorThreads(unittest.TestCase):
    @mock.patch('celery.beat.Scheduler.__init__', new=mock.Mock())
    @mock.patch('pulp.server.async.scheduler.EventMonitor')
    @mock.patch('pulp.server.async.scheduler.WorkerTimeoutMonitor')
    def test_spawn_pulp_monitor_threads(self, mock_worker_timeout_monitor, mock_event_monitor):
        my_scheduler = scheduler.Scheduler()

        my_scheduler.spawn_pulp_monitor_threads()

        mock_event_monitor.assert_called_once_with(my_scheduler._failure_watcher)
        self.assertTrue(mock_event_monitor.return_value.daemon)
        mock_event_monitor.return_value.start.assert_called_once()

        mock_worker_timeout_monitor.assert_called_once_with()
        self.assertTrue(mock_worker_timeout_monitor.return_value.daemon)
        mock_worker_timeout_monitor.return_value.start.assert_called_once()


class TestSchedulerTick(unittest.TestCase):
    @mock.patch('celery.beat.Scheduler.__init__', new=mock.Mock())
    @mock.patch('celery.beat.Scheduler.tick')
    def test_calls_superclass(self, mock_tick):
        sched_instance = scheduler.Scheduler()

        sched_instance.tick()

        mock_tick.assert_called_once_with()

    @mock.patch('celery.beat.Scheduler.__init__', new=mock.Mock())
    @mock.patch.object(scheduler.FailureWatcher, 'trim')
    @mock.patch('celery.beat.Scheduler.tick')
    def test_calls_trim(self, mock_tick, mock_trim):
        sched_instance = scheduler.Scheduler()

        sched_instance.tick()

        mock_trim.assert_called_once_with()


class TestSchedulerSetupSchedule(unittest.TestCase):

    @mock.patch('threading.Thread', new=mock.MagicMock())
    @mock.patch.object(scheduler.Scheduler, '_mongo_initialized', new=False)
    @mock.patch('itertools.imap')
    @mock.patch('pulp.server.async.scheduler.db_connection')
    def test_initialize_mongo_db_correctly(self, mock_db_connection, mock_imap):
        sched_instance = scheduler.Scheduler()

        sched_instance.setup_schedule()

        mock_db_connection.initialize.assert_called_once_with()
        self.assertTrue(scheduler.Scheduler._mongo_initialized)

    @mock.patch('threading.Thread', new=mock.MagicMock())
    @mock.patch.object(scheduler.Scheduler, '_mongo_initialized', new=True)
    @mock.patch('itertools.imap')
    @mock.patch('pulp.server.async.scheduler.db_connection')
    def test_ignore_mongo_db_when_appropriate(self, mock_db_connection, mock_imap):
        sched_instance = scheduler.Scheduler()

        sched_instance.setup_schedule()

        self.assertTrue(not mock_db_connection.initialize.called)
        self.assertTrue(scheduler.Scheduler._mongo_initialized)

    @mock.patch('threading.Thread', new=mock.MagicMock())
    @mock.patch('pulp.server.managers.schedule.utils.get_enabled', return_value=[])
    def test_loads_app_schedules(self, mock_get_enabled):
        sched_instance = scheduler.Scheduler()

        # make sure we have some real data to test with
        self.assertTrue(len(sched_instance.app.conf.CELERYBEAT_SCHEDULE) > 0)

        for key in sched_instance.app.conf.CELERYBEAT_SCHEDULE:
            self.assertTrue(key in sched_instance._schedule)
            self.assertTrue(isinstance(sched_instance._schedule.get(key), ScheduleEntry))

    @mock.patch('threading.Thread', new=mock.MagicMock())
    @mock.patch('pulp.server.managers.schedule.utils.get_enabled')
    def test_loads_db_schedules(self, mock_get_enabled):
        mock_get_enabled.return_value = SCHEDULES

        sched_instance = scheduler.Scheduler()
        # remove schedules we're not testing for
        for key in scheduler.app.conf.CELERYBEAT_SCHEDULE:
            del sched_instance._schedule[key]

        self.assertEqual(len(sched_instance._schedule), 2)
        self.assertTrue(isinstance(sched_instance._schedule.get('529f4bd93de3a31d0ec77338'),
                                   dispatch.ScheduleEntry))

        # make sure it chose the maximum enabled timestamp
        self.assertEqual(sched_instance._most_recent_timestamp, 1387218569.811224)
        # make sure the entry with no remaining runs does not go into the schedule
        self.assertTrue('529f4bd93de3a31d0ec77340' not in sched_instance._schedule)


class TestSchedulerScheduleChanged(unittest.TestCase):
    @mock.patch('threading.Thread', new=mock.MagicMock())
    @mock.patch('pulp.server.managers.schedule.utils.get_enabled')
    @mock.patch('pulp.server.managers.schedule.utils.get_updated_since')
    def test_count_changed(self, mock_updated_since, mock_get_enabled):
        mock_updated_since.return_value.count.return_value = 0
        mock_get_enabled.return_value = SCHEDULES
        sched_instance = scheduler.Scheduler()

        mock_get_enabled.return_value = mock.MagicMock()
        mock_get_enabled.return_value.count.return_value = sched_instance._loaded_from_db_count + 1

        self.assertTrue(sched_instance.schedule_changed is True)

    @mock.patch('threading.Thread', new=mock.MagicMock())
    @mock.patch('pulp.server.managers.schedule.utils.get_enabled')
    @mock.patch('pulp.server.managers.schedule.utils.get_updated_since')
    def test_new_updated(self, mock_updated_since, mock_get_enabled):
        mock_get_enabled.return_value = SCHEDULES
        sched_instance = scheduler.Scheduler()

        mock_get_enabled.return_value = mock.MagicMock()
        mock_get_enabled.return_value.count.return_value = sched_instance._loaded_from_db_count
        mock_updated_since.return_value.count.return_value = 1

        self.assertTrue(sched_instance.schedule_changed is True)

    @mock.patch('threading.Thread', new=mock.MagicMock())
    @mock.patch('pulp.server.managers.schedule.utils.get_enabled')
    @mock.patch('pulp.server.managers.schedule.utils.get_updated_since')
    def test_no_changes(self, mock_updated_since, mock_get_enabled):
        mock_updated_since.return_value.count.return_value = 0
        mock_get_enabled.return_value = SCHEDULES
        sched_instance = scheduler.Scheduler()

        mock_get_enabled.return_value = mock.MagicMock()
        # -1 because there is an ignored schedule that has 0 remaining runs
        mock_get_enabled.return_value.count.return_value = len(SCHEDULES) - 1

        self.assertTrue(sched_instance.schedule_changed is False)


class TestSchedulerSchedule(unittest.TestCase):
    @mock.patch('threading.Thread', new=mock.MagicMock())
    @mock.patch.object(scheduler.Scheduler, 'get_schedule')
    def test_schedule_is_None(self, mock_get_schedule):
        sched_instance = scheduler.Scheduler()
        sched_instance._schedule = None

        sched_instance.schedule

        # make sure it called the get_schedule() method inherited from the baseclass
        mock_get_schedule.assert_called_once_with()

    @mock.patch('threading.Thread', new=mock.MagicMock())
    @mock.patch.object(scheduler.Scheduler, 'setup_schedule')
    @mock.patch.object(scheduler.Scheduler, 'schedule_changed', new=True)
    def test_schedule_changed(self, mock_setup_schedule):
        sched_instance = scheduler.Scheduler()

        sched_instance.schedule

        # make sure it called the setup_schedule() method
        mock_setup_schedule.assert_called_once_with()

    @mock.patch('threading.Thread', new=mock.MagicMock())
    @mock.patch.object(scheduler.Scheduler, 'schedule_changed', return_value=False)
    @mock.patch.object(scheduler.Scheduler, 'setup_schedule')
    def test_schedule_returns_value(self, mock_setup_schedule, mock_schedule_changed):
        sched_instance = scheduler.Scheduler()
        sched_instance._schedule = mock.Mock()

        ret = sched_instance.schedule

        self.assertTrue(ret is sched_instance._schedule)


class TestSchedulerAdd(unittest.TestCase):
    @mock.patch('threading.Thread', new=mock.MagicMock())
    @mock.patch.object(scheduler.Scheduler, 'setup_schedule')
    def test_not_implemented(self, mock_setup_schedule):
        sched_instance = scheduler.Scheduler()

        self.assertRaises(NotImplementedError, sched_instance.add)


class TestSchedulerApplyAsync(unittest.TestCase):
    @mock.patch('threading.Thread', new=mock.MagicMock())
    @mock.patch.object(scheduler.Scheduler, 'setup_schedule')
    @mock.patch('celery.beat.Scheduler.apply_async')
    def test_not_custom_entry(self, mock_apply_async, mock_setup_schedule):
        sched_instance = scheduler.Scheduler()
        mock_entry = mock.MagicMock()

        ret = sched_instance.apply_async(mock_entry)

        self.assertTrue(ret is mock_apply_async.return_value)
        self.assertEqual(len(sched_instance._failure_watcher), 0)

    @mock.patch('threading.Thread', new=mock.MagicMock())
    @mock.patch.object(scheduler.Scheduler, 'setup_schedule')
    @mock.patch('celery.beat.Scheduler.apply_async')
    def test_celery_entry(self, mock_apply_async, mock_setup_schedule):
        sched_instance = scheduler.Scheduler()
        call = dispatch.ScheduledCall('PT1H', 'fake.task')
        entry = call.as_schedule_entry()

        sched_instance.apply_async(entry)

        self.assertEqual(len(sched_instance._failure_watcher), 0)

    @mock.patch('threading.Thread', new=mock.MagicMock())
    @mock.patch.object(scheduler.Scheduler, 'setup_schedule')
    @mock.patch('celery.beat.Scheduler.apply_async')
    def test_returns_superclass_value(self, mock_apply_async, mock_setup_schedule):
        sched_instance = scheduler.Scheduler()
        mock_entry = mock.MagicMock()

        ret = sched_instance.apply_async(mock_entry)

        self.assertTrue(ret is mock_apply_async.return_value)

    @mock.patch('threading.Thread', new=mock.MagicMock())
    @mock.patch.object(scheduler.Scheduler, 'setup_schedule')
    @mock.patch('celery.beat.Scheduler.apply_async')
    def test_no_failure_threshold(self, mock_apply_async, mock_setup_schedule):
        sched_instance = scheduler.Scheduler()
        entry = dispatch.ScheduledCall.from_db(SCHEDULES[1]).as_schedule_entry()

        sched_instance.apply_async(entry)

        # make sure the entry wasn't added, because it does not have a
        # failure threshold
        self.assertEqual(len(sched_instance._failure_watcher), 0)

    @mock.patch('threading.Thread', new=mock.MagicMock())
    @mock.patch.object(scheduler.Scheduler, 'setup_schedule')
    @mock.patch('celery.beat.Scheduler.apply_async')
    def test_failure_threshold(self, mock_apply_async, mock_setup_schedule):
        sched_instance = scheduler.Scheduler()
        entry = dispatch.ScheduledCall.from_db(SCHEDULES[0]).as_schedule_entry()

        sched_instance.apply_async(entry)

        # make sure the entry was added, because it has a failure threshold
        self.assertEqual(len(sched_instance._failure_watcher), 1)


class TestEventMonitorRun(unittest.TestCase):
    class SleepException(Exception):
        pass

    @mock.patch.object(scheduler.EventMonitor, 'monitor_events', spec_set=True)
    @mock.patch.object(scheduler.time, 'sleep', spec_set=True)
    def test_sleeps(self, mock_sleep, mock_monitor_events):
        # raising an exception is the only way we have to break out of the
        # infinite loop
        mock_sleep.side_effect = self.SleepException

        self.assertRaises(self.SleepException, scheduler.EventMonitor(mock.Mock()).run)

        # verify the frequency
        mock_sleep.assert_called_once_with(10)

    @mock.patch.object(scheduler._logger, 'error', spec_set=True)
    @mock.patch.object(scheduler.EventMonitor, 'monitor_events', spec_set=True)
    @mock.patch.object(scheduler.time, 'sleep', spec_set=True)
    def test_monitor_events(self, mock_sleep, mock_monitor_events, mock_log_error):

        # raising an exception is the only way we have to break out of the
        # infinite loop
        mock_monitor_events.side_effect = self.SleepException
        mock_log_error.side_effect = self.SleepException

        self.assertRaises(self.SleepException, scheduler.EventMonitor(mock.Mock()).run)

        mock_monitor_events.assert_called_once_with()

    @mock.patch.object(scheduler._logger, 'error', spec_set=True)
    @mock.patch.object(scheduler.EventMonitor, 'monitor_events', spec_set=True)
    @mock.patch.object(scheduler.time, 'sleep', spec_set=True)
    def test_logs_exception(self, mock_sleep, mock_monitor_events, mock_log_error):

        # raising an exception is the only way we have to break out of the
        # infinite loop
        mock_monitor_events.side_effect = self.SleepException
        mock_log_error.side_effect = self.SleepException

        self.assertRaises(self.SleepException, scheduler.EventMonitor(mock.Mock()).run)

        self.assertEqual(mock_log_error.call_count, 1)


class TestWorkerTimeoutMonitorRun(unittest.TestCase):
    class SleepException(Exception):
        pass

    @mock.patch.object(scheduler.WorkerTimeoutMonitor, 'check_workers', spec_set=True)
    @mock.patch.object(scheduler.time, 'sleep', spec_set=True)
    def test_sleeps(self, mock_sleep, mock_check_workers):
        # raising an exception is the only way we have to break out of the
        # infinite loop
        mock_sleep.side_effect = self.SleepException

        self.assertRaises(self.SleepException, scheduler.WorkerTimeoutMonitor().run)

        # verify the frequency
        mock_sleep.assert_called_once_with(60)

    @mock.patch.object(scheduler._logger, 'error', spec_set=True)
    @mock.patch.object(scheduler.WorkerTimeoutMonitor, 'check_workers', spec_set=True)
    @mock.patch.object(scheduler.time, 'sleep', spec_set=True)
    def test_checks_workers(self, mock_sleep, mock_check_workers, mock_log_error):

        # raising an exception is the only way we have to break out of the
        # infinite loop
        mock_check_workers.side_effect = self.SleepException
        mock_log_error.side_effect = self.SleepException

        self.assertRaises(self.SleepException, scheduler.WorkerTimeoutMonitor().run)

        mock_check_workers.assert_called_once_with()

    @mock.patch.object(scheduler._logger, 'error', spec_set=True)
    @mock.patch.object(scheduler.WorkerTimeoutMonitor, 'check_workers', spec_set=True)
    @mock.patch.object(scheduler.time, 'sleep', spec_set=True)
    def test_logs_exception(self, mock_sleep, mock_check_workers, mock_log_error):

        # raising an exception is the only way we have to break out of the
        # infinite loop
        mock_check_workers.side_effect = self.SleepException
        mock_log_error.side_effect = self.SleepException

        self.assertRaises(self.SleepException, scheduler.WorkerTimeoutMonitor().run)

        self.assertEqual(mock_log_error.call_count, 1)


class TestWorkerTimeoutMonitorCheckWorkers(unittest.TestCase):
    @mock.patch('pulp.server.managers.resources.filter_workers', spec_set=True)
    def test_calls_filter(self, mock_filter):
        mock_filter.return_value = []

        scheduler.WorkerTimeoutMonitor().check_workers()

        # verify that filter was called with the right argument
        self.assertEqual(mock_filter.call_count, 1)
        self.assertEqual(len(mock_filter.call_args[0]), 1)
        call_arg = mock_filter.call_args[0][0]
        self.assertTrue(isinstance(call_arg, Criteria))

        # make sure the timestamp being searched for is within the appropriate timeout,
        # plus a 1-second grace period to account for execution time of test code.
        timestamp = call_arg.filters['last_heartbeat']['$lt']
        self.assertTrue(isinstance(timestamp, datetime))
        self.assertTrue(datetime.utcnow() - timestamp <
                        timedelta(scheduler.WorkerTimeoutMonitor.WORKER_TIMEOUT_SECONDS + 1))

    @mock.patch('pulp.server.async.scheduler._delete_worker', spec_set=True)
    @mock.patch('pulp.server.managers.resources.filter_workers', spec_set=True)
    def test_deletes_workers(self, mock_filter, mock_delete_worker):
        mock_filter.return_value = [
            resources.Worker('name1', datetime.utcnow()),
            resources.Worker('name2', datetime.utcnow()),
        ]

        scheduler.WorkerTimeoutMonitor().check_workers()

        # make sure _delete_worker is only called for the two expected calls
        mock_delete_worker.assert_has_calls([mock.call('name1'), mock.call('name2')])


SCHEDULES = [
    {
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
        u'next_run': u'2013-12-17T00:36:53Z',
        u'principal': u"(dp0\nV_id\np1\nccopy_reg\n_reconstructor\np2\n(cbson.objectid\nObjectId\np3\nc__builtin__\nobject\np4\nNtp5\nRp6\nS'R \\xab\\x06\\xe1\\x9a\\x00\\x10\\xe1i\\x05\\x89'\np7\nbsVname\np8\nVadmin\np9\nsVroles\np10\n(lp11\nVsuper-users\np12\nasV_ns\np13\nVusers\np14\nsVlogin\np15\nVadmin\np16\nsVpassword\np17\nVV76Yol1XYgM=,S/G6o5UyMrn0xAwbQCqFcrXnfXTh84RWhunanCDkSCo=\np18\nsVid\np19\nV5220ab06e19a0010e1690589\np20\ns.",
        u'remaining_runs': None,
        u'resource': u'pulp:distributor:demo:puppet_distributor',
        u'schedule': u"ccopy_reg\n_reconstructor\np0\n(ccelery.schedules\nschedule\np1\nc__builtin__\nobject\np2\nNtp3\nRp4\n(dp5\nS'relative'\np6\nI00\nsS'nowfun'\np7\nNsS'run_every'\np8\ncdatetime\ntimedelta\np9\n(I0\nI60\nI0\ntp10\nRp11\nsb.",
        u'task': u'pulp.server.tasks.repository.publish',
        u'total_run_count': 1087,
    },
    {
        u'_id': u'529f4bd93de3a31d0ec77339',
        u'args': [u'demo2', u'puppet_distributor'],
        u'consecutive_failures': 0,
        u'enabled': True,
        u'failure_threshold': None,
        u'first_run': u'2013-12-04T15:35:53Z',
        u'iso_schedule': u'PT1M',
        u'kwargs': {u'overrides': {}},
        u'last_run_at': u'2013-12-17T00:35:53Z',
        u'last_updated': 1387218500.598727,
        u'next_run': u'2013-12-17T00:36:53Z',
        u'principal': u"(dp0\nV_id\np1\nccopy_reg\n_reconstructor\np2\n(cbson.objectid\nObjectId\np3\nc__builtin__\nobject\np4\nNtp5\nRp6\nS'R \\xab\\x06\\xe1\\x9a\\x00\\x10\\xe1i\\x05\\x89'\np7\nbsVname\np8\nVadmin\np9\nsVroles\np10\n(lp11\nVsuper-users\np12\nasV_ns\np13\nVusers\np14\nsVlogin\np15\nVadmin\np16\nsVpassword\np17\nVV76Yol1XYgM=,S/G6o5UyMrn0xAwbQCqFcrXnfXTh84RWhunanCDkSCo=\np18\nsVid\np19\nV5220ab06e19a0010e1690589\np20\ns.",
        u'remaining_runs': None,
        u'resource': u'pulp:distributor:demo:puppet_distributor',
        u'schedule': u"ccopy_reg\n_reconstructor\np0\n(ccelery.schedules\nschedule\np1\nc__builtin__\nobject\np2\nNtp3\nRp4\n(dp5\nS'relative'\np6\nI00\nsS'nowfun'\np7\nNsS'run_every'\np8\ncdatetime\ntimedelta\np9\n(I0\nI60\nI0\ntp10\nRp11\nsb.",
        u'task': u'pulp.server.tasks.repository.publish',
        u'total_run_count': 1087,
    },
    {
        u'_id': u'529f4bd93de3a31d0ec77340',
        u'args': [u'demo3', u'puppet_distributor'],
        u'consecutive_failures': 0,
        u'enabled': True,
        u'failure_threshold': 2,
        u'first_run': u'2013-12-04T15:35:53Z',
        u'iso_schedule': u'PT1M',
        u'kwargs': {u'overrides': {}},
        u'last_run_at': u'2013-12-17T00:35:53Z',
        u'last_updated': 1387218501.598727,
        u'next_run': u'2013-12-17T00:36:53Z',
        u'principal': u"(dp0\nV_id\np1\nccopy_reg\n_reconstructor\np2\n(cbson.objectid\nObjectId\np3\nc__builtin__\nobject\np4\nNtp5\nRp6\nS'R \\xab\\x06\\xe1\\x9a\\x00\\x10\\xe1i\\x05\\x89'\np7\nbsVname\np8\nVadmin\np9\nsVroles\np10\n(lp11\nVsuper-users\np12\nasV_ns\np13\nVusers\np14\nsVlogin\np15\nVadmin\np16\nsVpassword\np17\nVV76Yol1XYgM=,S/G6o5UyMrn0xAwbQCqFcrXnfXTh84RWhunanCDkSCo=\np18\nsVid\np19\nV5220ab06e19a0010e1690589\np20\ns.",
        u'remaining_runs': 0,
        u'resource': u'pulp:distributor:demo:puppet_distributor',
        u'schedule': u"ccopy_reg\n_reconstructor\np0\n(ccelery.schedules\nschedule\np1\nc__builtin__\nobject\np2\nNtp3\nRp4\n(dp5\nS'relative'\np6\nI00\nsS'nowfun'\np7\nNsS'run_every'\np8\ncdatetime\ntimedelta\np9\n(I0\nI60\nI0\ntp10\nRp11\nsb.",
        u'task': u'pulp.server.tasks.repository.publish',
        u'total_run_count': 1087,
    },
]
