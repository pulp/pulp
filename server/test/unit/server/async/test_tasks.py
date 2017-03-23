"""
This module contains tests for the pulp.server.async.tasks module.
"""
import unittest
import uuid
from datetime import datetime

import celery
from celery.app import defaults
from celery.result import AsyncResult

import mock
from mongoengine import ValidationError

from pulp import tasking
from pulp.common import dateutils
from pulp.common.constants import CALL_CANCELED_STATE, CALL_COMPLETED_STATE, SCHEDULER_WORKER_NAME
from pulp.common.tags import action_tag
from pulp.devel.unit.util import compare_dict
from pulp.server.db.model import TaskStatus, Worker
from pulp.server.db.reaper import queue_reap_expired_documents
from pulp.server.exceptions import NoWorkers, PulpCodedException, PulpException
from pulp.server.maintenance.monthly import queue_monthly_maintenance
from pulp.tasking import celery_app as app
from pulp.tasking.constants import TASKING_CONSTANTS

from ...base import PulpServerTests, ResourceReservationTests

# Worker names
WORKER_1 = 'worker-1'
WORKER_2 = 'worker-2'
WORKER_3 = 'worker-3'


class TestQueueReservedTask(ResourceReservationTests):

    def setUp(self):
        self.patch_a = mock.patch('pulp.server.async.tasks.get_worker_for_reservation')
        self.mock_get_worker_for_reservation = self.patch_a.start()

        self.patch_b = mock.patch('pulp.server.async.tasks._get_unreserved_worker')
        self.mock_get_unreserved_worker = self.patch_b.start()

        self.patch_c = mock.patch('pulp.server.async.tasks.time', autospec=True)
        self.mock_time = self.patch_c.start()

        self.patch_d = mock.patch('pulp.server.async.tasks.ReservedResource', autospec=True)
        self.mock_reserved_resource = self.patch_d.start()

        self.patch_e = mock.patch('pulp.server.async.tasks.celery', autospec=True)
        self.mock_celery = self.patch_e.start()
        self.mock_celery.tasks = {'task_name': mock.Mock()}

        self.patch_f = mock.patch('pulp.server.async.tasks._release_resource', autospec=True)
        self.mock__release_resource = self.patch_f.start()

        super(TestQueueReservedTask, self).setUp()

    def tearDown(self):
        self.patch_a.stop()
        self.patch_b.stop()
        self.patch_c.stop()
        self.patch_d.stop()
        self.patch_e.stop()
        self.patch_f.stop()
        super(TestQueueReservedTask, self).tearDown()

    def test_creates_and_saves_reserved_resource(self):
        self.mock_get_worker_for_reservation.return_value = Worker(
            name='worker1', last_heartbeat=datetime.utcnow())
        tasking._queue_reserved_task('task_name', 'my_task_id', 'my_resource_id', [1, 2], {'a': 2})
        self.mock_reserved_resource.assert_called_once_with(task_id='my_task_id',
                                                            worker_name='worker1',
                                                            resource_id='my_resource_id')
        self.mock_reserved_resource.return_value.save.assert_called_once_with()

    def test_dispatches_inner_task(self):
        self.mock_get_worker_for_reservation.return_value = Worker(
            name='worker1', last_heartbeat=datetime.utcnow())
        tasking._queue_reserved_task('task_name', 'my_task_id', 'my_resource_id', [1, 2], {'a': 2})
        apply_async = self.mock_celery.tasks['task_name'].apply_async
        apply_async.assert_called_once_with(1, 2, a=2, routing_key='worker1', task_id='my_task_id',
                                            exchange='C.dq')

    def test_dispatches__release_resource(self):
        self.mock_get_worker_for_reservation.return_value = Worker(
            name='worker1', last_heartbeat=datetime.utcnow())
        tasking._queue_reserved_task('task_name', 'my_task_id', 'my_resource_id', [1, 2], {'a': 2})
        self.mock__release_resource.apply_async.assert_called_once_with(('my_task_id',),
                                                                        routing_key='worker1',
                                                                        exchange='C.dq')

    def test_get_worker_for_reservation_breaks_out_of_loop(self):
        self.mock_get_worker_for_reservation.return_value = Worker(
            name='worker1', last_heartbeat=datetime.utcnow())
        tasking._queue_reserved_task('task_name', 'my_task_id', 'my_resource_id', [1, 2], {'a': 2})
        self.assertTrue(not self.mock_get_unreserved_worker.called)
        self.assertTrue(not self.mock_time.sleep.called)

    def test_get_unreserved_worker_breaks_out_of_loop(self):
        self.mock_get_worker_for_reservation.side_effect = NoWorkers()
        self.mock_get_unreserved_worker.return_value = Worker(name='worker1',
                                                              last_heartbeat=datetime.utcnow())
        tasking._queue_reserved_task('task_name', 'my_task_id', 'my_resource_id', [1, 2], {'a': 2})
        self.assertTrue(not self.mock_time.sleep.called)

    def test_loops_and_sleeps_waiting_for_available_worker(self):
        self.mock_get_worker_for_reservation.side_effect = NoWorkers()
        self.mock_get_unreserved_worker.side_effect = NoWorkers()

        class BreakOutException(Exception):
            pass

        def side_effect(*args):
            def second_call(*args):
                raise BreakOutException()
            self.mock_time.sleep.side_effect = second_call
            return None

        self.mock_time.sleep.side_effect = side_effect

        try:
            tasking._queue_reserved_task('task_name', 'my_task_id', 'my_resource_id', [1, 2],
                                         {'a': 2})
        except BreakOutException:
            pass
        else:
            self.fail('_queue_reserved_task should have raised a BreakOutException')

        self.mock_time.sleep.assert_has_calls([mock.call(0.25), mock.call(0.25)])


class TestDeleteWorker(ResourceReservationTests):

    def setUp(self):
        self.patch_a = mock.patch('pulp.server.async.tasks.ReservedResource', autospec=True)
        self.mock_reserved_resource = self.patch_a.start()

        self.patch_b = mock.patch('pulp.server.async.tasks.cancel', autospec=True)
        self.mock_cancel = self.patch_b.start()

        self.patch_c = mock.patch('pulp.server.async.tasks._logger', autospec=True)
        self.mock_logger = self.patch_c.start()

        self.patch_d = mock.patch('pulp.server.async.tasks._', autospec=True)
        self.mock_gettext = self.patch_d.start()

        self.patch_f = mock.patch('pulp.server.async.tasks.Worker', autospec=True)
        self.mock_worker = self.patch_f.start()

        self.patch_g = mock.patch('pulp.server.async.tasks.TaskStatus', autospec=True)
        self.mock_task_status = self.patch_g.start()

        self.patch_i = mock.patch('pulp.server.async.tasks.constants', autospec=True)
        self.mock_constants = self.patch_i.start()

        super(TestDeleteWorker, self).setUp()

    def tearDown(self):
        self.patch_a.stop()
        self.patch_b.stop()
        self.patch_c.stop()
        self.patch_d.stop()
        self.patch_f.stop()
        self.patch_g.stop()
        self.patch_i.stop()
        super(TestDeleteWorker, self).tearDown()

    def test_normal_shutdown_true_logs_correctly(self):
        tasking.delete_worker('worker1', normal_shutdown=True)
        self.assertTrue(self.mock_gettext.called)
        self.assertTrue(not self.mock_logger.error.called)

    def test_normal_shutdown_not_specified_logs(self):
        self.mock_gettext.return_value = 'asdf %(name)s asdf'
        tasking.delete_worker('worker1')
        self.mock_gettext.assert_called_once_with(
            'The worker named %(name)s is missing. Canceling the tasks in its queue.')
        self.mock_logger.error.assert_called_once_with('asdf worker1 asdf')

    def test_removes_all_associated_reserved_resource_entries(self):
        tasking.delete_worker(TASKING_CONSTANTS.RESOURCE_MANAGER_WORKER_NAME + '@worker1')
        self.assertTrue(self.mock_reserved_resource.objects.filter.called)
        remove = self.mock_reserved_resource.objects.filter.return_value.delete
        remove.assert_called_once_with()

    @mock.patch('pulp.server.async.tasks.Worker.objects')
    def test_removes_the_worker(self, mock_worker_objects):
        mock_document = mock.Mock()
        mock_get = mock.Mock()
        mock_get.get.return_value = [mock_document]
        mock_worker_objects.return_value = mock_get

        tasking.delete_worker('worker1')

        mock_document.delete.assert_called_once()

    @mock.patch('pulp.server.async.tasks.Worker.objects')
    def test_no_entry_for_worker_does_not_raise_exception(self, mock_worker_objects):
        mock_worker_objects.get.return_value = []
        try:
            tasking.delete_worker('worker1')
        except Exception:
            self.fail('delete_worker() on a Worker that is not in the database caused an '
                      'Exception')

    def test_cancels_all_found_task_status_objects(self):
        mock_task_id_a = mock.Mock()
        mock_task_id_b = mock.Mock()
        self.mock_task_status.objects.return_value = [{'task_id': mock_task_id_a},
                                                      {'task_id': mock_task_id_b}]
        tasking.delete_worker('worker1')

        self.mock_cancel.assert_has_calls([mock.call(mock_task_id_a), mock.call(mock_task_id_b)])


class TestReleaseResource(unittest.TestCase):

    def setUp(self):
        self.patch_a = mock.patch('pulp.server.async.tasks.ReservedResource', autospec=True)
        self.mock_reserved_resource = self.patch_a.start()

        self.patch_b = mock.patch('pulp.server.async.tasks.TaskStatus', autospec=True)
        self.mock_task_status = self.patch_b.start()

        self.patch_c = mock.patch('pulp.server.async.tasks.Task', autospec=True)
        self.mock_task = self.patch_c.start()

        self.patch_d = mock.patch('pulp.server.async.tasks.constants', autospec=True)
        self.mock_constants = self.patch_d.start()

        super(TestReleaseResource, self).setUp()

    def tearDown(self):
        self.patch_a.stop()
        self.patch_b.stop()
        self.patch_c.stop()
        self.patch_d.stop()
        super(TestReleaseResource, self).tearDown()

    def test_deletes_reserved_resource(self):
        mock_task_id = mock.Mock()
        tasking._release_resource(mock_task_id)
        self.mock_reserved_resource.objects.assert_called_once_with(task_id=mock_task_id)
        self.mock_reserved_resource.objects.return_value.delete.assert_called_once_with()

    def test_finds_running_task_by_uuid(self):
        mock_task_id = mock.Mock()
        tasking._release_resource(mock_task_id)
        filter_obj = self.mock_task_status.objects.filter
        filter_obj.assert_called_once_with(task_id=mock_task_id,
                                           state=self.mock_constants.CALL_RUNNING_STATE)

    def test_calls_on_failure_handler_if_task_id_is_not_final(self):
        self.mock_task_status.objects.filter.return_value = [mock.Mock()]
        mock_task = mock.Mock()
        self.mock_task.return_value = mock_task
        mock_task_id = mock.Mock()
        tasking._release_resource(mock_task_id)
        self.assertTrue(mock_task.on_failure.called)


class TestTaskResult(unittest.TestCase):

    def test_serialize(self):

        async_result = AsyncResult('foo')
        test_exception = PulpException('foo')
        task_status = TaskStatus(task_id='quux')
        result = tasking.TaskResult('foo', test_exception, [{'task_id': 'baz'},
                                                            async_result, "qux", task_status])
        serialized = result.serialize()
        self.assertEquals(serialized.get('result'), 'foo')
        compare_dict(test_exception.to_dict(), serialized.get('error'))
        self.assertEquals(serialized.get('spawned_tasks'), [{'task_id': 'baz'},
                                                            {'task_id': 'foo'},
                                                            {'task_id': 'qux'},
                                                            {'task_id': 'quux'}])


class TestReservedTaskMixinApplyAsyncWithReservation(ResourceReservationTests):

    def setUp(self):
        super(TestReservedTaskMixinApplyAsyncWithReservation, self).setUp()
        self.task = tasking.ReservedTaskMixin()
        self.task.name = 'dummy_task_name'
        self.resource_id = 'three_to_get_ready'
        self.resource_type = 'reserve_me'

        self.some_args = [1, 'b', 'iii']
        self.some_kwargs = {'1': 'for the money', '2': 'for the show', 'worker_name': WORKER_1,
                            'exchange': 'C.dq', 'tags': ['tag1', 'tag2']}

        self.task_patch = mock.patch('pulp.server.async.tasks._queue_reserved_task', autospec=True)
        self.mock__queue_reserved_task = self.task_patch.start()

        self.uuid_patch = mock.patch('pulp.server.async.tasks.uuid', autospec=True)
        self.mock_uuid = self.uuid_patch.start()
        self.mock_uuid.uuid4.return_value = uuid.uuid4()

        self.task_status_patch = mock.patch('pulp.server.async.tasks.TaskStatus', autospec=True)
        self.mock_task_status = self.task_status_patch.start()

        self.constants_patch = mock.patch('pulp.server.async.tasks.constants', autospec=True)
        self.mock_constants = self.constants_patch.start()

        self.result = self.task.apply_async_with_reservation(self.resource_type, self.resource_id,
                                                             *self.some_args, **self.some_kwargs)

    def tearDown(self):
        self.task_patch.stop()
        self.uuid_patch.stop()
        self.task_status_patch.stop()
        self.constants_patch.stop()
        super(TestReservedTaskMixinApplyAsyncWithReservation, self).tearDown()

    def test_apply_async_on__queue_reserved_task_called(self):
        expected_arguments = ['dummy_task_name', str(self.mock_uuid.uuid4.return_value),
                              'reserve_me:three_to_get_ready', tuple(self.some_args),
                              self.some_kwargs]
        self.mock__queue_reserved_task.apply_async.assert_called_once_with(
            queue=tasking.RESOURCE_MANAGER_QUEUE,
            args=expected_arguments)

    def test_task_status_created_and_saved(self):
        self.mock_task_status.assert_called_once_with(
            state=self.mock_constants.CALL_WAITING_STATE, task_type=self.task.name,
            task_id=str(self.mock_uuid.uuid4.return_value), tags=self.some_kwargs['tags'],
            group_id=None)
        save_with_set_on_insert = self.mock_task_status.return_value.save_with_set_on_insert
        save_with_set_on_insert.assert_called_once_with(
            fields_to_set_on_insert=['state', 'start_time'])

    def test_inner_task_id_returned(self):
        self.assertEqual(self.result, str(self.mock_uuid.uuid4.return_value))


class TestTaskOnSuccessHandler(ResourceReservationTests):

    @mock.patch('pulp.server.async.tasks.Task.request')
    def test_updates_task_status_correctly(self, mock_request):
        retval = 'random_return_value'
        task_id = str(uuid.uuid4())
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'routing_key': WORKER_2}
        mock_request.called_directly = False

        task_status = TaskStatus(task_id).save()
        self.assertEqual(task_status['state'], 'waiting')
        self.assertEqual(task_status['finish_time'], None)

        task = tasking.UserFacingTask()
        task.on_success(retval, task_id, args, kwargs)

        new_task_status = TaskStatus.objects(task_id=task_id).first()
        self.assertEqual(new_task_status['state'], 'finished')
        self.assertEqual(new_task_status['result'], retval)
        self.assertFalse(new_task_status['finish_time'] is None)
        # Make sure that parse_iso8601_datetime is able to parse the finish_time without errors
        dateutils.parse_iso8601_datetime(new_task_status['finish_time'])

    @mock.patch('pulp.server.async.tasks.Task.request')
    def test_spawned_task_status(self, mock_request):
        async_result = AsyncResult('foo-id')

        retval = tasking.TaskResult(error=PulpException('error-foo'),
                                    result='bar')
        retval.spawned_tasks = [async_result]

        task_id = str(uuid.uuid4())
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'routing_key': WORKER_2}
        mock_request.called_directly = False

        task_status = TaskStatus(task_id).save()
        self.assertEqual(task_status['state'], 'waiting')
        self.assertEqual(task_status['finish_time'], None)

        task = tasking.UserFacingTask()
        task.on_success(retval, task_id, args, kwargs)

        new_task_status = TaskStatus.objects(task_id=task_id).first()
        self.assertEqual(new_task_status['state'], 'finished')
        self.assertEqual(new_task_status['result'], 'bar')
        self.assertEqual(new_task_status['error']['description'], 'error-foo')
        self.assertFalse(new_task_status['finish_time'] is None)
        # Make sure that parse_iso8601_datetime is able to parse the finish_time without errors
        dateutils.parse_iso8601_datetime(new_task_status['finish_time'])
        self.assertEqual(new_task_status['spawned_tasks'], ['foo-id'])

    @mock.patch('pulp.server.async.tasks.Task.request')
    def test_spawned_task_dict(self, mock_request):
        retval = tasking.TaskResult(spawned_tasks=[{'task_id': 'foo-id'}], result='bar')

        task_id = str(uuid.uuid4())
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'routing_key': WORKER_2}
        mock_request.called_directly = False

        task_status = TaskStatus(task_id).save()
        self.assertEqual(task_status['state'], 'waiting')
        self.assertEqual(task_status['finish_time'], None)

        task = tasking.UserFacingTask()
        task.on_success(retval, task_id, args, kwargs)

        new_task_status = TaskStatus.objects(task_id=task_id).first()
        self.assertEqual(new_task_status['state'], 'finished')
        self.assertEqual(new_task_status['result'], 'bar')
        self.assertFalse(new_task_status['finish_time'] is None)
        self.assertEqual(new_task_status['spawned_tasks'], ['foo-id'])

    @mock.patch('pulp.server.async.tasks.Task.request')
    def test_async_result(self, mock_request):
        retval = AsyncResult('foo-id')

        task_id = str(uuid.uuid4())
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'routing_key': WORKER_2}
        mock_request.called_directly = False

        task_status = TaskStatus(task_id).save()
        self.assertEqual(task_status['state'], 'waiting')
        self.assertEqual(task_status['finish_time'], None)

        task = tasking.UserFacingTask()
        task.on_success(retval, task_id, args, kwargs)

        new_task_status = TaskStatus.objects(task_id=task_id).first()
        self.assertEqual(new_task_status['state'], 'finished')
        self.assertEqual(new_task_status['result'], None)
        self.assertFalse(new_task_status['finish_time'] is None)
        # Make sure that parse_iso8601_datetime is able to parse the finish_time without errors
        dateutils.parse_iso8601_datetime(new_task_status['finish_time'])
        self.assertEqual(new_task_status['spawned_tasks'], ['foo-id'])

    @mock.patch('pulp.server.async.tasks.Task.request')
    def test_with_canceled_task(self, mock_request):
        retval = 'random_return_value'
        task_id = str(uuid.uuid4())
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'routing_key': WORKER_2}
        mock_request.called_directly = False
        TaskStatus(task_id, state=CALL_CANCELED_STATE).save()
        task = tasking.UserFacingTask()

        # This should not update the task status to finished, since this task was canceled.
        task.on_success(retval, task_id, args, kwargs)

        updated_task_status = TaskStatus.objects(task_id=task_id).first()
        # Make sure the task is still canceled.
        self.assertEqual(updated_task_status['state'], CALL_CANCELED_STATE)
        self.assertEqual(updated_task_status['result'], retval)
        self.assertFalse(updated_task_status['finish_time'] is None)
        # Make sure that parse_iso8601_datetime is able to parse the finish_time without errors
        dateutils.parse_iso8601_datetime(updated_task_status['finish_time'])

    @mock.patch('pulp.server.async.tasks.Task.request')
    @mock.patch('pulp.server.managers.schedule.utils.reset_failure_count')
    def test_with_scheduled_call(self, mock_reset_failure, mock_request):
        retval = 'random_return_value'
        task_id = str(uuid.uuid4())
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'routing_key': WORKER_2,
                  'scheduled_call_id': '12345'}
        mock_request.called_directly = False
        TaskStatus(task_id).save()
        task = tasking.UserFacingTask()
        task.on_success(retval, task_id, args, kwargs)
        mock_reset_failure.assert_called_once_with('12345')

    @mock.patch('pulp.server.async.tasks.Task.request')
    @mock.patch('pulp.server.managers.schedule.utils.reset_failure_count')
    def test_with_scheduled_call_none(self, mock_reset_failure, mock_request):
        """
        Ensure that if scheduled_call_id  exists but is `None`, do not fail.
        """
        retval = 'random_return_value'
        task_id = str(uuid.uuid4())
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'routing_key': WORKER_2,
                  'scheduled_call_id': None}
        mock_request.called_directly = False
        TaskStatus(task_id).save()
        task = tasking.UserFacingTask()
        task.on_success(retval, task_id, args, kwargs)
        self.assertFalse(mock_reset_failure.called)


class TestTaskOnFailureHandler(ResourceReservationTests):

    @mock.patch('pulp.server.async.tasks.Task.request')
    def test_updates_task_status_correctly(self, mock_request):
        exc = Exception()
        task_id = str(uuid.uuid4())
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags']}

        class EInfo(object):
            """
            on_failure handler expects an instance of celery's ExceptionInfo class
            as one of the attributes. It stores string representation of traceback
            in it's traceback instance variable. This is a stub to imitate that behavior.
            """
            def __init__(self):
                self.traceback = "string_repr_of_traceback"

        einfo = EInfo()
        mock_request.called_directly = False

        task_status = TaskStatus(task_id).save()
        self.assertEqual(task_status['state'], 'waiting')
        self.assertEqual(task_status['finish_time'], None)
        self.assertEqual(task_status['traceback'], None)

        task = tasking.UserFacingTask()
        task.on_failure(exc, task_id, args, kwargs, einfo)

        new_task_status = TaskStatus.objects(task_id=task_id).first()
        self.assertEqual(new_task_status['state'], 'error')
        self.assertFalse(new_task_status['finish_time'] is None)
        # Make sure that parse_iso8601_datetime is able to parse the finish_time without errors
        dateutils.parse_iso8601_datetime(new_task_status['finish_time'])
        self.assertEqual(new_task_status['traceback'], einfo.traceback)

    @mock.patch('pulp.server.async.tasks.Task.request')
    @mock.patch('pulp.server.managers.schedule.utils.increment_failure_count')
    def test_with_scheduled_call(self, mock_increment_failure, mock_request):
        exc = Exception()
        task_id = str(uuid.uuid4())
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'scheduled_call_id': '12345'}

        class EInfo(object):
            """
            on_failure handler expects an instance of celery's ExceptionInfo class
            as one of the attributes. It stores string representation of traceback
            in it's traceback instance variable. This is a stub to imitate that behavior.
            """
            def __init__(self):
                self.traceback = "string_repr_of_traceback"

        einfo = EInfo()
        mock_request.called_directly = False
        TaskStatus(task_id).save()
        task = tasking.UserFacingTask()
        task.on_failure(exc, task_id, args, kwargs, einfo)
        mock_increment_failure.assert_called_once_with('12345')

    @mock.patch('pulp.server.async.tasks.Task.request')
    @mock.patch('pulp.server.managers.schedule.utils.increment_failure_count')
    def test_with_scheduled_call_none(self, mock_increment_failure, mock_request):
        exc = Exception()
        task_id = str(uuid.uuid4())
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'scheduled_call_id': None}

        class EInfo(object):
            """
            on_failure handler expects an instance of celery's ExceptionInfo class
            as one of the attributes. It stores string representation of traceback
            in it's traceback instance variable. This is a stub to imitate that behavior.
            """
            def __init__(self):
                self.traceback = "string_repr_of_traceback"

        einfo = EInfo()
        mock_request.called_directly = False
        TaskStatus(task_id).save()
        task = tasking.UserFacingTask()
        task.on_failure(exc, task_id, args, kwargs, einfo)
        self.assertFalse(mock_increment_failure.called)


class TestTaskApplyAsync(ResourceReservationTests):

    @mock.patch('celery.Task.apply_async')
    def test_creates_task_status(self, apply_async):
        args = [1, 'b', 'iii']
        kwargs = {'a': 'for the money', 'tags': ['test_tags'], 'routing_key': WORKER_1}
        apply_async.return_value = celery.result.AsyncResult('test_task_id')
        task = tasking.UserFacingTask()

        task.apply_async(*args, **kwargs)

        task_statuses = TaskStatus.objects()
        self.assertEqual(task_statuses.count(), 1)
        new_task_status = task_statuses[0]
        self.assertEqual(new_task_status['task_id'], 'test_task_id')
        self.assertIsNone(new_task_status['group_id'])
        self.assertEqual(new_task_status['worker_name'], WORKER_1)
        self.assertEqual(new_task_status['tags'], kwargs['tags'])
        self.assertEqual(new_task_status['state'], 'waiting')
        self.assertEqual(new_task_status['error'], None)
        self.assertEqual(new_task_status['spawned_tasks'], [])
        self.assertEqual(new_task_status['progress_report'], {})
        self.assertEqual(new_task_status['task_type'], 'pulp.server.async.tasks.Task')
        self.assertEqual(new_task_status['start_time'], None)
        self.assertEqual(new_task_status['finish_time'], None)
        self.assertEqual(new_task_status['result'], None)

    @mock.patch('celery.Task.apply_async')
    def test_creates_task_status_with_group_id(self, apply_async):
        args = [1, 'b', 'iii']
        group_id = uuid.uuid4()
        kwargs = {'a': 'for the money', 'tags': ['test_tags'], 'routing_key': WORKER_1,
                  'group_id': group_id}
        apply_async.return_value = celery.result.AsyncResult('test_task_id')
        task = tasking.UserFacingTask()

        task.apply_async(*args, **kwargs)

        task_statuses = TaskStatus.objects()
        self.assertEqual(task_statuses.count(), 1)
        new_task_status = task_statuses[0]
        self.assertEqual(new_task_status['task_id'], 'test_task_id')
        self.assertEqual(new_task_status['group_id'], group_id)
        self.assertEqual(new_task_status['worker_name'], WORKER_1)
        self.assertEqual(new_task_status['tags'], kwargs['tags'])
        self.assertEqual(new_task_status['state'], 'waiting')
        self.assertEqual(new_task_status['error'], None)
        self.assertEqual(new_task_status['spawned_tasks'], [])
        self.assertEqual(new_task_status['progress_report'], {})
        self.assertEqual(new_task_status['task_type'], 'pulp.server.async.tasks.Task')
        self.assertEqual(new_task_status['start_time'], None)
        self.assertEqual(new_task_status['finish_time'], None)
        self.assertEqual(new_task_status['result'], None)

    @mock.patch('celery.Task.apply_async')
    def test_exception_task_status_with_bad_group_id(self, apply_async):
        args = [1, 'b', 'iii']
        kwargs = {'a': 'for the money', 'tags': ['test_tags'], 'routing_key': WORKER_1,
                  'group_id': 'string-id'}
        apply_async.return_value = celery.result.AsyncResult('test_task_id')
        task = tasking.UserFacingTask()

        self.assertRaises(ValidationError, task.apply_async, *args, **kwargs)

    @mock.patch('celery.Task.apply_async')
    def test_calls_parent_apply_async(self, apply_async):
        args = [1, 'b', 'iii']
        kwargs = {'a': 'for the money', 'tags': ['test_tags'], 'routing_key': 'asdf'}
        apply_async.return_value = celery.result.AsyncResult('test_task_id')
        task = tasking.UserFacingTask()

        task.apply_async(*args, **kwargs)

        apply_async.assert_called_once_with(1, 'b', 'iii', a='for the money', routing_key='asdf')

    @mock.patch('celery.Task.apply_async')
    def test_calls_parent_apply_async_with_group_id(self, apply_async):
        args = [1, 'b', 'iii']
        kwargs = {'a': 'for the money', 'tags': ['test_tags'], 'routing_key': 'asdf',
                  'group_id': uuid.uuid4()}
        apply_async.return_value = celery.result.AsyncResult('test_task_id')
        task = tasking.UserFacingTask()

        task.apply_async(*args, **kwargs)

        apply_async.assert_called_once_with(1, 'b', 'iii', a='for the money', routing_key='asdf')

    @mock.patch('celery.Task.apply_async')
    def test_saves_default_routing_key_as_worker_name(self, apply_async):
        args = [1, 'b', 'iii']
        kwargs = {'a': 'for the money', 'tags': ['test_tags']}
        apply_async.return_value = celery.result.AsyncResult('test_task_id')
        task = tasking.UserFacingTask()

        task.apply_async(*args, **kwargs)

        task_statuses = TaskStatus.objects()
        self.assertEqual(task_statuses.count(), 1)
        new_task_status = task_statuses[0]
        self.assertEqual(new_task_status['task_id'], 'test_task_id')
        self.assertEqual(new_task_status['worker_name'],
                         defaults.NAMESPACES['CELERY']['DEFAULT_ROUTING_KEY'].default)
        self.assertEqual(new_task_status['tags'], kwargs['tags'])
        self.assertEqual(new_task_status['state'], 'waiting')

    @mock.patch('celery.Task.apply_async')
    def test_saves_passed_in_routing_key_as_worker_name(self, apply_async):
        args = [1, 'b', 'iii']
        kwargs = {'a': 'for the money', 'tags': ['test_tags'], 'routing_key': 'othername'}
        apply_async.return_value = celery.result.AsyncResult('test_task_id')
        task = tasking.UserFacingTask()

        task.apply_async(*args, **kwargs)

        task_statuses = TaskStatus.objects()
        self.assertEqual(task_statuses.count(), 1)
        new_task_status = task_statuses[0]
        self.assertEqual(new_task_status['task_id'], 'test_task_id')
        self.assertEqual(new_task_status['worker_name'], 'othername')
        self.assertEqual(new_task_status['tags'], kwargs['tags'])
        self.assertEqual(new_task_status['state'], 'waiting')

    @mock.patch('celery.Task.apply_async')
    def test_task_status_not_modified_when_task_status_exists(self, apply_async):
        args = [1, 'b', 'iii']
        kwargs = {'a': 'for the money', 'tags': ['test_tags']}
        task_id = 'test_task_id'
        TaskStatus(task_id, 'test-worker', state=CALL_CANCELED_STATE).save()
        apply_async.return_value = celery.result.AsyncResult(task_id)

        task = tasking.UserFacingTask()
        task.apply_async(*args, **kwargs)

        task_status = TaskStatus.objects(task_id=task_id).first()
        self.assertEqual(task_status['state'], 'canceled')
        self.assertEqual(task_status['start_time'], None)

    @mock.patch('celery.Task.apply_async')
    def test_returns_apply_async_result(self, apply_async):
        args = [1, 'b', 'iii']
        kwargs = {'a': 'for the money', 'tags': ['test_tags']}
        async_result = celery.result.AsyncResult('test_task_id')
        apply_async.return_value = async_result
        task = tasking.UserFacingTask()

        result = task.apply_async(*args, **kwargs)

        self.assertEqual(result, async_result)

    @mock.patch('celery.Task.apply_async')
    def test_returns_apply_async_result_including_tags(self, apply_async):
        args = [1, 'b', 'iii']
        kwargs = {'a': 'for the money', 'tags': ['test_tags']}
        async_result = celery.result.AsyncResult('test_task_id')
        apply_async.return_value = async_result
        task = tasking.UserFacingTask()

        result = task.apply_async(*args, **kwargs)

        self.assertEqual(result.tags, ['test_tags'])


class TestTaskThrows(unittest.TestCase):
    """
    Exceptions listed in the "throws" collection will not have their stack
    traces get auto-logged by celery.
    """
    def test_throws_pulp_coded_exception(self):
        self.assertTrue(PulpCodedException in tasking.UserFacingTask.throws)


class TestCancel(PulpServerTests):
    """
    Test the tasks.cancel() function.
    """
    def setUp(self):
        PulpServerTests.setUp(self)
        TaskStatus.objects().delete()

    def tearDown(self):
        PulpServerTests.tearDown(self)
        TaskStatus.objects().delete()

    @mock.patch('pulp.server.async.tasks.controller.revoke', autospec=True)
    @mock.patch('pulp.server.async.tasks._logger', autospec=True)
    def test_cancel_successful(self, _logger, revoke):
        task_id = '1234abcd'
        TaskStatus(task_id).save()
        tasking.cancel(task_id)

        revoke.assert_called_once_with(task_id, terminate=True)
        self.assertEqual(_logger.info.call_count, 1)
        log_msg = _logger.info.mock_calls[0][1][0]
        self.assertTrue(task_id in log_msg)
        self.assertTrue('Task canceled' in log_msg)
        task_status = TaskStatus.objects(task_id=task_id).first()
        self.assertEqual(task_status['state'], CALL_CANCELED_STATE)

    @mock.patch('pulp.server.async.tasks.controller.revoke', autospec=True)
    @mock.patch('pulp.server.async.tasks._logger', autospec=True)
    def test_cancel_after_task_finished(self, _logger, revoke):
        """
        Test that canceling a task that is already finished results in no change
        to the task state.
        """
        task_id = '1234abcd'
        TaskStatus(task_id, 'test_worker', state=CALL_COMPLETED_STATE).save()

        tasking.cancel(task_id)
        task_status = TaskStatus.objects(task_id=task_id).first()
        self.assertEqual(task_status['state'], CALL_COMPLETED_STATE)

    @mock.patch('pulp.server.async.tasks.controller.revoke', autospec=True)
    @mock.patch('pulp.server.async.tasks._logger', autospec=True)
    def test_cancel_after_task_canceled(self, *unused_mocks):
        """
        Test that canceling a task that was already canceled results in no change
        to the task state.
        """
        task_id = '1234abcd'
        TaskStatus(task_id, 'test_worker', state=CALL_CANCELED_STATE).save()

        tasking.cancel(task_id)
        task_status = TaskStatus.objects(task_id=task_id).first()
        self.assertEqual(task_status['state'], CALL_CANCELED_STATE)


class TestGetCurrentTaskId(unittest.TestCase):

    @mock.patch('pulp.server.async.tasks.current_task')
    def test_get_task_id(self, mock_current_task):
        mock_current_task.request.id = 'foo'
        self.assertEquals('foo', tasking.get_current_task_id())

    def test_get_task_id_not_in_task(self):
        self.assertEquals(None, tasking.get_current_task_id())


class TestScheduledTasks(unittest.TestCase):

    @mock.patch('pulp.server.db.reaper.reap_expired_documents.apply_async')
    def test_reap_expired_documents_apply_async(self, mock_reaper_apply_async):
        queue_reap_expired_documents()
        mock_reaper_apply_async.assert_called_once_with(tags=[action_tag('reaper')])

    @mock.patch('pulp.server.maintenance.monthly.monthly_maintenance.apply_async')
    def test_monthly_maintenance_apply_async(self, mock_monthly_apply_async):
        queue_monthly_maintenance()
        mock_monthly_apply_async.assert_called_once_with(tags=[action_tag('monthly')])


class TestGetWorkerForReservation(ResourceReservationTests):

    @mock.patch('pulp.server.async.tasks.Worker.objects')
    @mock.patch('pulp.server.async.tasks.ReservedResource')
    def test_existing_reservation_correctly_found(self, mock_reserved_resource,
                                                  mock_worker_objects):
        get_objects = mock_reserved_resource.objects
        tasking.get_worker_for_reservation('resource1')
        get_objects.assert_called_once_with(resource_id='resource1')
        get_objects.return_value.first.assert_called_once_with()

    @mock.patch('pulp.server.async.tasks.Worker.objects')
    @mock.patch('pulp.server.async.tasks.ReservedResource')
    def test_correct_worker_returned(self, mock_reserved_resource, mock_worker_objects):
        find_one = mock_reserved_resource.objects.return_value.first
        find_one.return_value = {'worker_name': 'worker1'}
        mock_worker_objects.return_value.first.return_value = find_one.return_value
        result = tasking.get_worker_for_reservation('resource1')
        self.assertTrue(result is find_one.return_value)

    @mock.patch('pulp.server.async.tasks.ReservedResource')
    def test_no_workers_raised_if_no_reservations(self, mock_reserved_resource):
        find_one = mock_reserved_resource.objects.return_value.first
        find_one.return_value = False
        try:
            tasking.get_worker_for_reservation('resource1')
        except NoWorkers:
            pass
        else:
            self.fail("NoWorkers() Exception should have been raised.")


class TestGetUnreservedWorker(ResourceReservationTests):

    @mock.patch('pulp.server.async.tasks.ReservedResource')
    def test_reserved_resources_queried_correctly(self, mock_reserved_resource):
        find = mock_reserved_resource.objects.all
        find.return_value = [{'worker_name': 'a'}, {'worker_name': 'b'}]
        try:
            tasking._get_unreserved_worker()
        except NoWorkers:
            pass
        else:
            self.fail("NoWorkers() Exception should have been raised.")
        find.assert_called_once_with()

    @mock.patch('pulp.server.async.tasks.Worker.objects')
    @mock.patch('pulp.server.async.tasks.ReservedResource')
    def test_worker_returned_when_one_worker_is_not_reserved(self, mock_reserved_resource,
                                                             mock_worker_objects):
        get_online = mock_worker_objects.get_online
        get_online.return_value = [{'name': 'a'}, {'name': 'b'}]
        mock_reserved_resource.objects.all.return_value = [{'worker_name': 'a'}]
        result = tasking._get_unreserved_worker()
        self.assertEqual(result, {'name': 'b'})

    @mock.patch('pulp.server.async.tasks.Worker.objects')
    @mock.patch('pulp.server.async.tasks.ReservedResource')
    def test_no_workers_raised_when_all_workers_reserved(self, mock_reserved_resource, mock_worker):
        mock_worker.objects.return_value = [{'name': 'a'}, {'name': 'b'}]
        find = mock_reserved_resource.objects
        find.return_value = [{'worker_name': 'a'}, {'worker_name': 'b'}]
        try:
            tasking._get_unreserved_worker()
        except NoWorkers:
            pass
        else:
            self.fail("NoWorkers() Exception should have been raised.")

    @mock.patch('pulp.server.async.tasks.Worker.objects')
    @mock.patch('pulp.server.async.tasks.ReservedResource')
    def test_no_workers_raised_when_there_are_no_workers(self, mock_reserved_resource, mock_worker):
        mock_worker.objects.return_value = []
        find = mock_reserved_resource.objects
        find.return_value = [{'worker_name': 'a'}, {'worker_name': 'b'}]
        try:
            tasking._get_unreserved_worker()
        except NoWorkers:
            pass
        else:
            self.fail("NoWorkers() Exception should have been raised.")

    def test_is_worker(self):
        self.assertTrue(tasking._is_worker("a_worker@some.hostname"))

    def test_is_not_worker_is_scheduler(self):
        self.assertEquals(tasking._is_worker(SCHEDULER_WORKER_NAME + "@some.hostname"), False)

    def test_is_not_worker_is_resource_mgr(self):
        self.assertEquals(tasking._is_worker(
            TASKING_CONSTANTS.RESOURCE_MANAGER_WORKER_NAME + "@some.hostname"), False)


class TestPulpTask(unittest.TestCase):

    def test_check_task_type(self):
        """
        This test looks through celery registry and asserts that each task entry in it is
        a subclass of PulpTask.
        This test should not be adjusted, unless you are really sure what are you doing.
        """

        for task_name, task in app.celery.tasking.iteritems():
            if task_name.startswith('pulp'):
                if not isinstance(task, tasking.PulpTask):
                    self.fail('Task named %s must have %s as an ancestor'
                              % (task_name, tasking.PulpTask))
