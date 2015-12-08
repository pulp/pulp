from datetime import datetime, timedelta
import unittest
import platform

from celery.beat import ScheduleEntry
import mock
from mongoengine import NotUniqueError

from pulp.common.constants import RESOURCE_MANAGER_WORKER_NAME, SCHEDULER_WORKER_NAME
from pulp.server.async import scheduler
from pulp.server.async.celery_instance import celery as app
from pulp.server.db.model import dispatch, Worker
from pulp.server.managers.factory import initialize


initialize()


class TestEventMonitorEvents(unittest.TestCase):
    def setUp(self):
        self.event_monitor = scheduler.EventMonitor()

    @mock.patch('pulp.server.async.scheduler.app.events.Receiver')
    def test_handlers_declared(self, mock_receiver):
        self.event_monitor.monitor_events()

        self.assertEqual(mock_receiver.call_count, 1)
        self.assertEqual(mock_receiver.return_value.capture.call_count, 1)
        handlers = mock_receiver.call_args[1]['handlers']

        self.assertTrue('worker-heartbeat' in handlers)
        self.assertTrue('worker-offline' in handlers)
        self.assertTrue('worker-online' in handlers)

    @mock.patch('pulp.server.async.scheduler.app.connection')
    @mock.patch('pulp.server.async.scheduler.app.events.Receiver')
    def test_connection_passed(self, mock_receiver, mock_connection):
        self.event_monitor.monitor_events()
        self.assertTrue(mock_receiver.call_args[0][0] is
                        mock_connection.return_value.__enter__.return_value)
        capture = mock_receiver.return_value.capture
        capture.assert_called_once_with(limit=None, timeout=None, wakeup=True)


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
    @mock.patch('pulp.server.async.scheduler.CeleryProcessTimeoutMonitor')
    def test_spawn_pulp_monitor_threads(self, mock_celery_timeout_monitor, mock_event_monitor):
        my_scheduler = scheduler.Scheduler()

        my_scheduler.spawn_pulp_monitor_threads()

        mock_event_monitor.assert_called_once_with()
        self.assertTrue(mock_event_monitor.return_value.daemon)
        mock_event_monitor.return_value.start.assert_called_once()

        mock_celery_timeout_monitor.assert_called_once_with()
        self.assertTrue(mock_celery_timeout_monitor.return_value.daemon)
        mock_celery_timeout_monitor.return_value.start.assert_called_once()


class TestSchedulerTick(unittest.TestCase):
    @mock.patch('celery.beat.Scheduler.__init__', new=mock.Mock())
    @mock.patch('celery.beat.Scheduler.tick')
    @mock.patch('pulp.server.async.scheduler.worker_watcher')
    @mock.patch('pulp.server.async.scheduler.CeleryBeatLock')
    def test_calls_superclass(self, mock_celerybeatlock, mock_worker_watcher, mock_tick):
        sched_instance = scheduler.Scheduler()

        sched_instance.tick()

        mock_tick.assert_called_once_with()

    @mock.patch('celery.beat.Scheduler.__init__', new=mock.Mock())
    @mock.patch('celery.beat.Scheduler.tick')
    @mock.patch('pulp.server.async.scheduler.platform.node')
    @mock.patch('pulp.server.async.scheduler.time')
    @mock.patch('pulp.server.async.scheduler.worker_watcher')
    @mock.patch('pulp.server.async.scheduler.CeleryBeatLock')
    def test_calls_handle_heartbeat(self, mock_celerybeatlock, mock_worker_watcher, time, node, mock_tick):
        sched_instance = scheduler.Scheduler()
        time.time.return_value = 1449261335.275528
        node.return_value = 'some_host'

        sched_instance.tick()

        expected_event = {'timestamp': 1449261335.275528, 'local_received': 1449261335.275528,
                          'type': 'scheduler-event', 'hostname': 'scheduler@some_host'}
        mock_heartbeat.assert_called_once_with(expected_event)
        mock_worker_watcher.assert_called_once()

    @mock.patch('celery.beat.Scheduler.__init__', new=mock.Mock())
    @mock.patch('pulp.server.async.scheduler.datetime')
    @mock.patch('pulp.server.async.scheduler.worker_watcher')
    @mock.patch('pulp.server.async.scheduler.CeleryBeatLock')
    @mock.patch('celery.beat.Scheduler.tick')
    def test_heartbeat_lock_insert_success(self, mock_tick, mock_celerybeatlock,
                                           mock_worker_watcher, mock_timestamp):

        sched_instance = scheduler.Scheduler()
        sched_instance.tick()

        lock_timestamp = mock_timestamp.utcnow()
        celerybeat_name = "scheduler" + "@" + platform.node()

        mock_celerybeatlock.assert_called_once_with(
            timestamp=lock_timestamp, celerybeat_name=celerybeat_name)
        mock_celerybeatlock.objects().save().assert_called_once()

    @mock.patch('celery.beat.Scheduler.__init__', new=mock.Mock())
    @mock.patch('pulp.server.async.scheduler.worker_watcher')
    @mock.patch('pulp.server.async.scheduler.CeleryBeatLock')
    @mock.patch('celery.beat.Scheduler.tick')
    def test_heartbeat_lock_update(self, mock_tick, mock_celerybeatlock, mock_worker_watcher):

        mock_celerybeatlock.objects.return_value.update.return_value = 1

        sched_instance = scheduler.Scheduler()
        sched_instance.tick()

        mock_tick.assert_called_once_with()

    @mock.patch('celery.beat.Scheduler.__init__', new=mock.Mock())
    @mock.patch('pulp.server.async.scheduler.worker_watcher')
    @mock.patch('pulp.server.async.scheduler.CeleryBeatLock')
    @mock.patch('celery.beat.Scheduler.tick')
    def test_heartbeat_lock_delete(self, mock_tick, mock_celerybeatlock, mock_worker_watcher):

        mock_celerybeatlock.objects.return_value.update.return_value = 0

        sched_instance = scheduler.Scheduler()
        sched_instance.tick()

        mock_tick.assert_called_once_with()

        mock_celerybeatlock.objects().delete().assert_called_once()

    @mock.patch('celery.beat.Scheduler.__init__', new=mock.Mock())
    @mock.patch('pulp.server.async.scheduler.worker_watcher')
    @mock.patch('pulp.server.async.scheduler.CeleryBeatLock')
    @mock.patch('celery.beat.Scheduler.tick')
    def test_heartbeat_lock_exception(self, mock_tick, mock_celerybeatlock, mock_worker_watcher):

        mock_celerybeatlock.objects.return_value.update.return_value = 0
        mock_celerybeatlock.return_value.save.side_effect = NotUniqueError()

        sched_instance = scheduler.Scheduler()
        sched_instance.tick()

        self.assertFalse(mock_tick.called)


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
    @mock.patch('pulp.server.async.scheduler.Scheduler._mongo_initialized', True)
    @mock.patch('pulp.server.managers.schedule.utils.get_enabled', return_value=[])
    def test_loads_app_schedules(self, mock_get_enabled):
        sched_instance = scheduler.Scheduler()

        # make sure we have some real data to test with
        self.assertTrue(len(sched_instance.app.conf.CELERYBEAT_SCHEDULE) > 0)

        for key in sched_instance.app.conf.CELERYBEAT_SCHEDULE:
            self.assertTrue(key in sched_instance._schedule)
            self.assertTrue(isinstance(sched_instance._schedule.get(key), ScheduleEntry))

    @mock.patch('threading.Thread', new=mock.MagicMock())
    @mock.patch('pulp.server.async.scheduler.Scheduler._mongo_initialized', True)
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
    @mock.patch('pulp.server.async.scheduler.Scheduler._mongo_initialized', True)
    @mock.patch('pulp.server.managers.schedule.utils.get_enabled')
    @mock.patch('pulp.server.managers.schedule.utils.get_updated_since')
    def test_count_changed(self, mock_updated_since, mock_get_enabled):
        """
        This test ensures that if the number of enabled schedules changes, the schedule_changed
        property returns True.
        """
        mock_updated_since.return_value.count.return_value = 0
        mock_get_enabled.return_value = SCHEDULES
        sched_instance = scheduler.Scheduler()

        mock_get_enabled.return_value = mock.MagicMock()
        mock_get_enabled.return_value.count.return_value = sched_instance._loaded_from_db_count + 1

        self.assertTrue(sched_instance.schedule_changed is True)

    @mock.patch('threading.Thread', new=mock.MagicMock())
    @mock.patch('pulp.server.async.scheduler.Scheduler._mongo_initialized', True)
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
    @mock.patch('pulp.server.async.scheduler.Scheduler._mongo_initialized', True)
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
    @mock.patch('pulp.server.async.scheduler.Scheduler._mongo_initialized', True)
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


class TestEventMonitorRun(unittest.TestCase):
    class SleepException(Exception):
        pass

    @mock.patch.object(scheduler.EventMonitor, 'monitor_events', spec_set=True)
    @mock.patch.object(scheduler.time, 'sleep', spec_set=True)
    def test_sleeps(self, mock_sleep, mock_monitor_events):
        # raising an exception is the only way we have to break out of the
        # infinite loop
        mock_sleep.side_effect = self.SleepException

        self.assertRaises(self.SleepException, scheduler.EventMonitor().run)

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

        self.assertRaises(self.SleepException, scheduler.EventMonitor().run)

        mock_monitor_events.assert_called_once_with()

    @mock.patch.object(scheduler._logger, 'error', spec_set=True)
    @mock.patch.object(scheduler.EventMonitor, 'monitor_events', spec_set=True)
    @mock.patch.object(scheduler.time, 'sleep', spec_set=True)
    def test_logs_exception(self, mock_sleep, mock_monitor_events, mock_log_error):

        # raising an exception is the only way we have to break out of the
        # infinite loop
        mock_monitor_events.side_effect = self.SleepException
        mock_log_error.side_effect = self.SleepException

        self.assertRaises(self.SleepException, scheduler.EventMonitor().run)

        self.assertEqual(mock_log_error.call_count, 1)


class TestCeleryProcessTimeoutMonitorRun(unittest.TestCase):

    class SleepException(Exception):
        pass

    @mock.patch.object(scheduler.CeleryProcessTimeoutMonitor, 'check_celery_processes',
                       spec_set=True)
    @mock.patch.object(scheduler.time, 'sleep', spec_set=True)
    def test_sleeps(self, mock_sleep, mock_check_celery_processes):
        # raising an exception is the only way we have to break out of the
        # infinite loop
        mock_sleep.side_effect = self.SleepException

        self.assertRaises(self.SleepException, scheduler.CeleryProcessTimeoutMonitor().run)

        # verify the frequency
        mock_sleep.assert_called_once_with(60)

    @mock.patch.object(scheduler._logger, 'error', spec_set=True)
    @mock.patch.object(scheduler.CeleryProcessTimeoutMonitor, 'check_celery_processes',
                       spec_set=True)
    @mock.patch.object(scheduler.time, 'sleep', spec_set=True)
    def test_checks_workers(self, mock_sleep, mock_check_celery_processes, mock_log_error):

        # raising an exception is the only way we have to break out of the
        # infinite loop
        mock_check_celery_processes.side_effect = self.SleepException
        mock_log_error.side_effect = self.SleepException

        self.assertRaises(self.SleepException, scheduler.CeleryProcessTimeoutMonitor().run)

        mock_check_celery_processes.assert_called_once_with()

    @mock.patch.object(scheduler._logger, 'error', spec_set=True)
    @mock.patch.object(scheduler.CeleryProcessTimeoutMonitor, 'check_celery_processes',
                       spec_set=True)
    @mock.patch.object(scheduler.time, 'sleep', spec_set=True)
    def test_logs_exception(self, mock_sleep, mock_check_celery_processes, mock_log_error):

        # raising an exception is the only way we have to break out of the
        # infinite loop
        mock_check_celery_processes.side_effect = self.SleepException
        mock_log_error.side_effect = self.SleepException

        self.assertRaises(self.SleepException, scheduler.CeleryProcessTimeoutMonitor().run)

        self.assertEqual(mock_log_error.call_count, 1)


class TestCeleryProcessTimeoutMonitorCheckCeleryProcesses(unittest.TestCase):

    @mock.patch('pulp.server.async.scheduler.Worker', spec_set=True)
    def test_queries_all_workers(self, mock_worker):
        mock_worker.return_value = []

        scheduler.CeleryProcessTimeoutMonitor().check_celery_processes()

        mock_worker.objects.all.assert_called_once_with()

    @mock.patch('pulp.server.async.scheduler._delete_worker', spec_set=True)
    @mock.patch('pulp.server.async.scheduler.Worker', spec_set=True)
    def test_deletes_workers(self, mock_worker, mock_delete_worker):
        mock_worker.objects.all.return_value = [
            Worker(name='name1', last_heartbeat=datetime.utcnow() - timedelta(seconds=400)),
            Worker(name='name2', last_heartbeat=datetime.utcnow()),
        ]

        scheduler.CeleryProcessTimeoutMonitor().check_celery_processes()

        # make sure _delete_worker is only called for the old worker
        mock_delete_worker.assert_has_calls([mock.call('name1')])

    @mock.patch('pulp.server.async.scheduler._delete_worker', spec_set=True)
    @mock.patch('pulp.server.async.scheduler.Worker', spec_set=True)
    @mock.patch('pulp.server.async.scheduler._logger', spec_set=True)
    def test_logs_scheduler_missing(self, mock__logger, mock_worker, mock_delete_worker):
        mock_worker.objects.all.return_value = [
            Worker(name=RESOURCE_MANAGER_WORKER_NAME, last_heartbeat=datetime.utcnow()),
            Worker(name='name2', last_heartbeat=datetime.utcnow()),
        ]

        scheduler.CeleryProcessTimeoutMonitor().check_celery_processes()

        mock__logger.error.assert_called_once_with(
            'There are 0 pulp_celerybeat processes running. Pulp will not operate '
            'correctly without at least one pulp_celerybeat process running.')

    @mock.patch('pulp.server.async.scheduler._delete_worker', spec_set=True)
    @mock.patch('pulp.server.async.scheduler.Worker', spec_set=True)
    @mock.patch('pulp.server.async.scheduler._logger', spec_set=True)
    def test_logs_resource_manager_missing(self, mock__logger, mock_worker, mock_delete_worker):
        mock_worker.objects.all.return_value = [
            Worker(name=SCHEDULER_WORKER_NAME, last_heartbeat=datetime.utcnow()),
            Worker(name='name2', last_heartbeat=datetime.utcnow()),
        ]

        scheduler.CeleryProcessTimeoutMonitor().check_celery_processes()

        mock__logger.error.assert_called_once_with(
            'There are 0 pulp_resource_manager processes running. Pulp will not operate '
            'correctly without at least one pulp_resource_mananger process running.')

    @mock.patch('pulp.server.async.scheduler._delete_worker', spec_set=True)
    @mock.patch('pulp.server.async.scheduler.Worker', spec_set=True)
    @mock.patch('pulp.server.async.scheduler._logger', spec_set=True)
    def test_debug_logging(self, mock__logger, mock_worker, mock_delete_worker):
        mock_worker.objects.all.return_value = [
            Worker(name='name1', last_heartbeat=datetime.utcnow() - timedelta(seconds=400)),
            Worker(name='name2', last_heartbeat=datetime.utcnow()),
            Worker(name=RESOURCE_MANAGER_WORKER_NAME, last_heartbeat=datetime.utcnow()),
            Worker(name=SCHEDULER_WORKER_NAME, last_heartbeat=datetime.utcnow()),
        ]

        scheduler.CeleryProcessTimeoutMonitor().check_celery_processes()
        mock__logger.debug.assert_has_calls([
            mock.call('Checking if pulp_workers, pulp_celerybeat, or '
                      'pulp_resource_manager processes are missing for more than 300 seconds'),
            mock.call('1 pulp_worker processes, 1 pulp_celerybeat processes, '
                      'and 1 pulp_resource_manager processes')
        ])


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
        u'principal': u"(dp0\nV_id\np1\nccopy_reg\n_reconstructor\np2\n(cbson.objectid\nObjectId\n"
                      u"p3\nc__builtin__\nobject\np4\nNtp5\nRp6\nS'R \\xab\\x06\\xe1\\x9a\\x00\\x10"
                      u"\\xe1i\\x05\\x89'\np7\nbsVname\np8\nVadmin\np9\nsVroles\np10\n(lp11\n"
                      u"Vsuper-users\np12\nasV_ns\np13\nVusers\np14\nsVlogin\np15\nVadmin\np16\n"
                      u"sVpassword\np17\n"
                      u"VV76Yol1XYgM=,S/G6o5UyMrn0xAwbQCqFcrXnfXTh84RWhunanCDkSCo=\np18\nsVid\n"
                      u"p19\nV5220ab06e19a0010e1690589\np20\ns.",
        u'remaining_runs': None,
        u'resource': u'pulp:distributor:demo:puppet_distributor',
        u'schedule': u"ccopy_reg\n_reconstructor\np0\n(ccelery.schedules\nschedule\np1\n"
                     u"c__builtin__\nobject\np2\nNtp3\nRp4\n(dp5\nS'relative'\np6\nI00\n"
                     u"sS'nowfun'\np7\nNsS'run_every'\np8\ncdatetime\ntimedelta\np9\n(I0\nI60\nI0\n"
                     u"tp10\nRp11\nsb.",
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
        u'principal': u"(dp0\nV_id\np1\nccopy_reg\n_reconstructor\np2\n(cbson.objectid\nObjectId\n"
                      u"p3\nc__builtin__\nobject\np4\nNtp5\nRp6\nS'R \\xab\\x06\\xe1\\x9a\\x00"
                      u"\\x10\\xe1i\\x05\\x89'\np7\nbsVname\np8\nVadmin\np9\nsVroles\np10\n(lp11\n"
                      u"Vsuper-users\np12\nasV_ns\np13\nVusers\np14\nsVlogin\np15\nVadmin\np16\n"
                      u"sVpassword\np17\n"
                      u"VV76Yol1XYgM=,S/G6o5UyMrn0xAwbQCqFcrXnfXTh84RWhunanCDkSCo=\np18\nsVid\n"
                      u"p19\nV5220ab06e19a0010e1690589\np20\ns.",
        u'remaining_runs': None,
        u'resource': u'pulp:distributor:demo:puppet_distributor',
        u'schedule': u"ccopy_reg\n_reconstructor\np0\n(ccelery.schedules\nschedule\np1\n"
                     u"c__builtin__\nobject\np2\nNtp3\nRp4\n(dp5\nS'relative'\np6\nI00\n"
                     u"sS'nowfun'\np7\nNsS'run_every'\np8\ncdatetime\ntimedelta\np9\n(I0\nI60\nI0\n"
                     u"tp10\nRp11\nsb.",
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
        u'principal': u"(dp0\nV_id\np1\nccopy_reg\n_reconstructor\np2\n(cbson.objectid\nObjectId\n"
                      u"p3\nc__builtin__\nobject\np4\nNtp5\nRp6\nS'R \\xab\\x06\\xe1\\x9a\\x00\\x10"
                      u"\\xe1i\\x05\\x89'\np7\nbsVname\np8\nVadmin\np9\nsVroles\np10\n(lp11\n"
                      u"Vsuper-users\np12\nasV_ns\np13\nVusers\np14\nsVlogin\np15\nVadmin\np16\n"
                      u"sVpassword\np17\n"
                      u"VV76Yol1XYgM=,S/G6o5UyMrn0xAwbQCqFcrXnfXTh84RWhunanCDkSCo=\np18\nsVid\n"
                      u"p19\nV5220ab06e19a0010e1690589\np20\ns.",
        u'remaining_runs': 0,
        u'resource': u'pulp:distributor:demo:puppet_distributor',
        u'schedule': u"ccopy_reg\n_reconstructor\np0\n(ccelery.schedules\nschedule\np1\n"
                     u"c__builtin__\nobject\np2\nNtp3\nRp4\n(dp5\nS'relative'\np6\nI00\n"
                     u"sS'nowfun'\np7\nNsS'run_every'\np8\ncdatetime\ntimedelta\np9\n(I0\nI60\nI0\n"
                     u"tp10\nRp11\nsb.",
        u'task': u'pulp.server.tasks.repository.publish',
        u'total_run_count': 1087,
    },
]
