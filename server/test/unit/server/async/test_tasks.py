"""
This module contains tests for the pulp.server.async.tasks module.
"""
from datetime import datetime
import signal
import unittest
import uuid

from celery.app import defaults
from celery.result import AsyncResult
import celery
import mock

from ...base import PulpServerTests, ResourceReservationTests
from pulp.common import dateutils
from pulp.common.constants import CALL_CANCELED_STATE, CALL_FINISHED_STATE
from pulp.common.tags import action_tag
from pulp.devel.unit.util import compare_dict
from pulp.server.exceptions import PulpException
from pulp.server.async import tasks
from pulp.server.async.task_status_manager import TaskStatusManager
from pulp.server.db.model.dispatch import TaskStatus
from pulp.server.db.model.resources import Worker, ReservedResource
from pulp.server.db.reaper import queue_reap_expired_documents
from pulp.server.exceptions import NoWorkers
from pulp.server.maintenance.monthly import queue_monthly_maintenance


# Worker names
WORKER_1 = 'worker-1'
WORKER_2 = 'worker-2'
WORKER_3 = 'worker-3'


class TestQueueReservedTask(ResourceReservationTests):

    def setUp(self):
        self.patch_a = mock.patch('pulp.server.async.tasks.resources.get_worker_for_reservation',
                                  autospec=True)
        self.mock_get_worker_for_reservation = self.patch_a.start()

        self.patch_b = mock.patch('pulp.server.async.tasks.resources.get_unreserved_worker',
                                  autospec=True)
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
        self.mock_get_worker_for_reservation.return_value = Worker('worker1', datetime.utcnow())
        tasks._queue_reserved_task('task_name', 'my_task_id', 'my_resource_id', [1,2], {'a':2})
        self.mock_reserved_resource.assert_called_once_with('my_task_id', 'worker1',
                                                            'my_resource_id')
        self.mock_reserved_resource.return_value.save.assert_called_once_with()

    def test_dispatches_inner_task(self):
        self.mock_get_worker_for_reservation.return_value = Worker('worker1', datetime.utcnow())
        tasks._queue_reserved_task('task_name', 'my_task_id', 'my_resource_id', [1,2], {'a':2})
        apply_async = self.mock_celery.tasks['task_name'].apply_async
        apply_async.assert_called_once_with(1, 2, a=2, routing_key='worker1', task_id='my_task_id',
                                            exchange='C.dq')

    def test_dispatches__release_resource(self):
        self.mock_get_worker_for_reservation.return_value = Worker('worker1', datetime.utcnow())
        tasks._queue_reserved_task('task_name', 'my_task_id', 'my_resource_id', [1,2], {'a':2})
        self.mock__release_resource.apply_async.assert_called_once_with(('my_task_id',),
                                                                        routing_key='worker1',
                                                                        exchange='C.dq')

    def test_get_worker_for_reservation_breaks_out_of_loop(self):
        self.mock_get_worker_for_reservation.return_value = Worker('worker1', datetime.utcnow())
        tasks._queue_reserved_task('task_name', 'my_task_id', 'my_resource_id', [1,2], {'a':2})
        self.assertTrue(not self.mock_get_unreserved_worker.called)
        self.assertTrue(not self.mock_time.sleep.called)

    def test_get_unreserved_worker_breaks_out_of_loop(self):
        self.mock_get_worker_for_reservation.side_effect = NoWorkers()
        self.mock_get_unreserved_worker.return_value = Worker('worker1', datetime.utcnow())
        tasks._queue_reserved_task('task_name', 'my_task_id', 'my_resource_id', [1,2], {'a':2})
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
            tasks._queue_reserved_task('task_name', 'my_task_id', 'my_resource_id', [1, 2],
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

        self.patch_c = mock.patch('pulp.server.async.tasks.logger', autospec=True)
        self.mock_logger = self.patch_c.start()

        self.patch_d = mock.patch('pulp.server.async.tasks._', autospec=True)
        self.mock_gettext = self.patch_d.start()

        self.patch_e = mock.patch('pulp.server.async.tasks.resources', autospec=True)
        self.mock_resources = self.patch_e.start()

        self.patch_f = mock.patch('pulp.server.async.tasks.Worker', autospec=True)
        self.mock_worker = self.patch_f.start()

        self.patch_g = mock.patch('pulp.server.async.tasks.TaskStatusManager', autospec=True)
        self.mock_task_status_manager = self.patch_g.start()

        self.patch_h = mock.patch('pulp.server.async.tasks.Criteria', autospec=True)
        self.mock_criteria = self.patch_h.start()

        self.patch_i = mock.patch('pulp.server.async.tasks.constants', autospec=True)
        self.mock_constants = self.patch_i.start()

        super(TestDeleteWorker, self).setUp()

    def tearDown(self):
        self.patch_a.stop()
        self.patch_b.stop()
        self.patch_c.stop()
        self.patch_d.stop()
        self.patch_e.stop()
        self.patch_f.stop()
        self.patch_g.stop()
        self.patch_h.stop()
        self.patch_i.stop()
        super(TestDeleteWorker, self).tearDown()

    def test_normal_shutdown_true_logs_correctly(self):
        tasks._delete_worker('worker1', normal_shutdown=True)
        self.assertTrue(not self.mock_gettext.called)
        self.assertTrue(not self.mock_logger.error.called)

    def test_normal_shutdown_not_specified_logs(self):
        self.mock_gettext.return_value = 'asdf %(name)s asdf'
        tasks._delete_worker('worker1')
        self.mock_gettext.assert_called_once_with(
            'The worker named %(name)s is missing. Canceling the tasks in its queue.')
        self.mock_logger.error.assert_called_once_with('asdf worker1 asdf')

    def test_removes_all_associated_reserved_resource_entries(self):
        tasks._delete_worker('worker1')
        self.assertTrue(self.mock_reserved_resource.get_collection.called)
        remove = self.mock_reserved_resource.get_collection.return_value.remove
        remove.assert_called_once_with({'worker_name': 'worker1'})

    def test_criteria_to_find_all_worker_is_correct(self):
        tasks._delete_worker('worker1')
        self.assertEqual(self.mock_criteria.mock_calls[0], mock.call(filters={'_id': 'worker1'}))

    def test_criteria_is_used_in_filter_workers(self):
        tasks._delete_worker('worker1')
        self.mock_resources.filter_workers.assert_called_once_with(self.mock_criteria.return_value)

    def test_removes_the_worker(self):
        mock_worker = mock.Mock()
        self.mock_resources.filter_workers.return_value = tuple([mock_worker])
        tasks._delete_worker('worker1')
        mock_worker.delete.assert_called_once_with()

    def test_no_entry_for_worker_does_not_raise_exception(self):
        self.mock_resources.filter_workers.return_value = []
        try:
            tasks._delete_worker('worker1')
        except Exception:
            self.fail('_delete_worker() on a Worker that is not in the database caused an '
                      'Exception')

    def test_makes_worker_object_from_bson(self):
        tasks._delete_worker('worker1')
        self.mock_worker.from_bson.assert_called_once_with({'_id': 'worker1'})

    def test_criteria_to_find_task_status_is_correct(self):
        tasks._delete_worker('worker1')
        expected_call = mock.call(
            filters={'worker_name': self.mock_worker.from_bson.return_value.name,
                     'state': {'$in': self.mock_constants.CALL_INCOMPLETE_STATES}})
        self.assertEqual(self.mock_criteria.mock_calls[1], expected_call)

    def test_cancels_all_found_task_status_objects(self):
        mock_task_id_a = mock.Mock()
        mock_task_id_b = mock.Mock()
        self.mock_task_status_manager.find_by_criteria.return_value = [{'task_id': mock_task_id_a},
                                                                       {'task_id': mock_task_id_b}]
        tasks._delete_worker('worker1')

        find_by_criteria = self.mock_task_status_manager.find_by_criteria
        find_by_criteria.assert_called_once_with(self.mock_criteria.return_value)

        self.mock_cancel.assert_has_calls([mock.call(mock_task_id_a), mock.call(mock_task_id_b)])


class TestReleaseResource(ResourceReservationTests):
    """
    Test the _release_resource() Task.
    """
    def test_resource_not_in_resource_map(self):
        """
        Test _release_resource() with a resource that is not in the database. This should be
        gracefully handled, and result in no changes to the database.
        """
        # Set up two workers
        worker_1 = Worker(WORKER_1, datetime.utcnow())
        worker_1.save()
        worker_2 = Worker(WORKER_2, datetime.utcnow())
        worker_2.save()
        # Set up two resource reservations, using our workers from above
        reserved_resource_1 = ReservedResource(uuid.uuid4(), worker_1.name, 'resource_1')
        reserved_resource_1.save()
        reserved_resource_2 = ReservedResource(uuid.uuid4(), worker_2.name, 'resource_2')
        reserved_resource_2.save()

        # This should not raise any Exception, but should also not alter either the Worker
        # collection or the ReservedResource collection
        tasks._release_resource('made_up_resource_id')

        # Make sure that the workers collection has not been altered
        worker_collection = Worker.get_collection()
        self.assertEqual(worker_collection.count(), 2)
        worker_1 = worker_collection.find_one({'_id': worker_1.name})
        self.assertTrue(worker_1)
        worker_2 = worker_collection.find_one({'_id': worker_2.name})
        self.assertTrue(worker_2)
        # Make sure that the reserved resources collection has not been altered
        rrc = ReservedResource.get_collection()
        self.assertEqual(rrc.count(), 2)
        rr_1 = rrc.find_one({'_id': reserved_resource_1.task_id})
        self.assertEqual(rr_1['worker_name'], reserved_resource_1.worker_name)
        self.assertEqual(rr_1['resource_id'], 'resource_1')
        rr_2 = rrc.find_one({'_id': reserved_resource_2.task_id})
        self.assertEqual(rr_2['worker_name'], reserved_resource_2.worker_name)
        self.assertEqual(rr_2['resource_id'], 'resource_2')

    def test_resource_in_resource_map(self):
        """
        Test _release_resource() with a valid resource. This should remove the resource from the
        database.
        """
        # Set up two workers
        now = datetime.utcnow()
        worker_1 = Worker(WORKER_1, now)
        worker_1.save()
        worker_2 = Worker(WORKER_2, now)
        worker_2.save()
        # Set up two reserved resources
        reserved_resource_1 = ReservedResource(uuid.uuid4(), worker_1.name, 'resource_1')
        reserved_resource_1.save()
        reserved_resource_2 = ReservedResource(uuid.uuid4(), worker_2.name, 'resource_2')
        reserved_resource_2.save()

        # This should remove resource_2 from the _resource_map.
        tasks._release_resource(reserved_resource_2.task_id)

        # resource_2 should have been removed from the database
        rrc = ReservedResource.get_collection()
        self.assertEqual(rrc.count(), 1)
        rr_1 = rrc.find_one({'_id': reserved_resource_1.task_id})
        self.assertEqual(rr_1['worker_name'], reserved_resource_1.worker_name)
        self.assertEqual(rr_1['resource_id'], 'resource_1')


class TestTaskResult(unittest.TestCase):

    def test_serialize(self):

        async_result = AsyncResult('foo')
        test_exception = PulpException('foo')
        result = tasks.TaskResult('foo', test_exception, [{'task_id': 'baz'}, async_result, "qux"])
        serialized = result.serialize()
        self.assertEquals(serialized.get('result'), 'foo')
        compare_dict(test_exception.to_dict(), serialized.get('error'))
        self.assertEquals(serialized.get('spawned_tasks'), [{'task_id': 'baz'},
                                                            {'task_id': 'foo'},
                                                            {'task_id': 'qux'}])


class TestReservedTaskMixinApplyAsyncWithReservation(ResourceReservationTests):

    def setUp(self):
        super(TestReservedTaskMixinApplyAsyncWithReservation, self).setUp()
        self.task = tasks.ReservedTaskMixin()
        self.task.name = 'dummy_task_name'
        self.resource_id = 'three_to_get_ready'
        self.resource_type = 'reserve_me'

        self.some_args = [1, 'b', 'iii']
        self.some_kwargs = {'1': 'for the money', '2': 'for the show', 'worker_name': WORKER_1,
                            'exchange': 'C.dq', 'tags': ['tag1','tag2']}

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
            queue=tasks.RESOURCE_MANAGER_QUEUE,
            args=expected_arguments)

    def test_task_status_created_and_saved(self):
        self.mock_task_status.assert_called_once_with(
            state=self.mock_constants.CALL_WAITING_STATE, task_type=self.task.name,
            task_id=str( self.mock_uuid.uuid4.return_value), tags=self.some_kwargs['tags'])
        save = self.mock_task_status.return_value.save
        save.assert_called_once_with(fields_to_set_on_insert=['state', 'start_time'])

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

        task_status = TaskStatusManager.create_task_status(task_id)
        self.assertEqual(task_status['state'], 'waiting')
        self.assertEqual(task_status['finish_time'], None)

        task = tasks.Task()
        task.on_success(retval, task_id, args, kwargs)

        new_task_status = TaskStatusManager.find_by_task_id(task_id)
        self.assertEqual(new_task_status['state'], 'finished')
        self.assertEqual(new_task_status['result'], retval)
        self.assertFalse(new_task_status['finish_time'] is None)
        # Make sure that parse_iso8601_datetime is able to parse the finish_time without errors
        dateutils.parse_iso8601_datetime(new_task_status['finish_time'])

    @mock.patch('pulp.server.async.tasks.Task.request')
    def test_spawned_task_status(self, mock_request):
        async_result = AsyncResult('foo-id')

        retval = tasks.TaskResult(error=PulpException('error-foo'),
                                  result='bar')
        retval.spawned_tasks = [async_result]

        task_id = str(uuid.uuid4())
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'routing_key': WORKER_2}
        mock_request.called_directly = False

        task_status = TaskStatusManager.create_task_status(task_id)
        self.assertEqual(task_status['state'], 'waiting')
        self.assertEqual(task_status['finish_time'], None)

        task = tasks.Task()
        task.on_success(retval, task_id, args, kwargs)

        new_task_status = TaskStatusManager.find_by_task_id(task_id)
        self.assertEqual(new_task_status['state'], 'finished')
        self.assertEqual(new_task_status['result'], 'bar')
        self.assertEqual(new_task_status['error']['description'], 'error-foo')
        self.assertFalse(new_task_status['finish_time'] is None)
        # Make sure that parse_iso8601_datetime is able to parse the finish_time without errors
        dateutils.parse_iso8601_datetime(new_task_status['finish_time'])
        self.assertEqual(new_task_status['spawned_tasks'], ['foo-id'])

    @mock.patch('pulp.server.async.tasks.Task.request')
    def test_spawned_task_dict(self, mock_request):
        retval = tasks.TaskResult(spawned_tasks=[{'task_id': 'foo-id'}], result='bar')

        task_id = str(uuid.uuid4())
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'routing_key': WORKER_2}
        mock_request.called_directly = False

        task_status = TaskStatusManager.create_task_status(task_id)
        self.assertEqual(task_status['state'], 'waiting')
        self.assertEqual(task_status['finish_time'], None)

        task = tasks.Task()
        task.on_success(retval, task_id, args, kwargs)

        new_task_status = TaskStatusManager.find_by_task_id(task_id)
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

        task_status = TaskStatusManager.create_task_status(task_id)
        self.assertEqual(task_status['state'], 'waiting')
        self.assertEqual(task_status['finish_time'], None)

        task = tasks.Task()
        task.on_success(retval, task_id, args, kwargs)

        new_task_status = TaskStatusManager.find_by_task_id(task_id)
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
        TaskStatusManager.create_task_status(task_id, state=CALL_CANCELED_STATE)
        task = tasks.Task()

        # This should not update the task status to finished, since this task was canceled.
        task.on_success(retval, task_id, args, kwargs)

        updated_task_status = TaskStatusManager.find_by_task_id(task_id)
        # Make sure the task is still canceled.
        self.assertEqual(updated_task_status['state'], CALL_CANCELED_STATE)
        self.assertEqual(updated_task_status['result'], retval)
        self.assertFalse(updated_task_status['finish_time'] is None)
        # Make sure that parse_iso8601_datetime is able to parse the finish_time without errors
        dateutils.parse_iso8601_datetime(updated_task_status['finish_time'])


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

        task_status = TaskStatusManager.create_task_status(task_id)
        self.assertEqual(task_status['state'], 'waiting')
        self.assertEqual(task_status['finish_time'], None)
        self.assertEqual(task_status['traceback'], None)

        task = tasks.Task()
        task.on_failure(exc, task_id, args, kwargs, einfo)

        new_task_status = TaskStatusManager.find_by_task_id(task_id)
        self.assertEqual(new_task_status['state'], 'error')
        self.assertFalse(new_task_status['finish_time'] is None)
        # Make sure that parse_iso8601_datetime is able to parse the finish_time without errors
        dateutils.parse_iso8601_datetime(new_task_status['finish_time'])
        self.assertEqual(new_task_status['traceback'], einfo.traceback)


class TestTaskApplyAsync(ResourceReservationTests):

    @mock.patch('celery.Task.apply_async')
    def test_creates_task_status(self, apply_async):
        args = [1, 'b', 'iii']
        kwargs = {'a': 'for the money', 'tags': ['test_tags'], 'routing_key': WORKER_1}
        apply_async.return_value = celery.result.AsyncResult('test_task_id')
        task = tasks.Task()

        task.apply_async(*args, **kwargs)

        task_statuses = list(TaskStatusManager.find_all())
        self.assertEqual(len(task_statuses), 1)
        new_task_status = task_statuses[0]
        self.assertEqual(new_task_status['task_id'], 'test_task_id')
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
    def test_calls_parent_apply_async(self, apply_async):
        args = [1, 'b', 'iii']
        kwargs = {'a': 'for the money', 'tags': ['test_tags'], 'routing_key': 'asdf'}
        apply_async.return_value = celery.result.AsyncResult('test_task_id')
        task = tasks.Task()

        task.apply_async(*args, **kwargs)

        apply_async.assert_called_once_with(1, 'b', 'iii', a='for the money', routing_key='asdf')

    @mock.patch('celery.Task.apply_async')
    def test_saves_default_routing_key_as_worker_name(self, apply_async):
        args = [1, 'b', 'iii']
        kwargs = {'a': 'for the money', 'tags': ['test_tags']}
        apply_async.return_value = celery.result.AsyncResult('test_task_id')
        task = tasks.Task()

        task.apply_async(*args, **kwargs)

        task_statuses = list(TaskStatusManager.find_all())
        self.assertEqual(len(task_statuses), 1)
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
        task = tasks.Task()

        task.apply_async(*args, **kwargs)

        task_statuses = list(TaskStatusManager.find_all())
        self.assertEqual(len(task_statuses), 1)
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
        TaskStatusManager.create_task_status(task_id, 'test-worker', state=CALL_CANCELED_STATE)
        apply_async.return_value = celery.result.AsyncResult(task_id)

        task = tasks.Task()
        task.apply_async(*args, **kwargs)

        task_status = TaskStatusManager.find_by_task_id(task_id)
        self.assertEqual(task_status['state'], 'canceled')
        self.assertEqual(task_status['start_time'], None)

    @mock.patch('celery.Task.apply_async')
    def test_returns_apply_async_result(self, apply_async):
        args = [1, 'b', 'iii']
        kwargs = {'a': 'for the money', 'tags': ['test_tags']}
        async_result = celery.result.AsyncResult('test_task_id')
        apply_async.return_value = async_result
        task = tasks.Task()

        result = task.apply_async(*args, **kwargs)

        self.assertEqual(result, async_result)

    @mock.patch('celery.Task.apply_async')
    def test_returns_apply_async_result_including_tags(self, apply_async):
        args = [1, 'b', 'iii']
        kwargs = {'a': 'for the money', 'tags': ['test_tags']}
        async_result = celery.result.AsyncResult('test_task_id')
        apply_async.return_value = async_result
        task = tasks.Task()

        result = task.apply_async(*args, **kwargs)

        self.assertEqual(result.tags, ['test_tags'])


class TestCancel(PulpServerTests):
    """
    Test the tasks.cancel() function.
    """
    def setUp(self):
        PulpServerTests.setUp(self)
        TaskStatus.get_collection().remove()

    def tearDown(self):
        PulpServerTests.tearDown(self)
        TaskStatus.get_collection().remove()

    @mock.patch('pulp.server.async.tasks.controller.revoke', autospec=True)
    @mock.patch('pulp.server.async.tasks.logger', autospec=True)
    def test_cancel_successful(self, logger, revoke):
        task_id = '1234abcd'
        TaskStatusManager.create_task_status(task_id)
        tasks.cancel(task_id)

        revoke.assert_called_once_with(task_id, terminate=True)
        self.assertEqual(logger.info.call_count, 1)
        log_msg = logger.info.mock_calls[0][1][0]
        self.assertTrue(task_id in log_msg)
        self.assertTrue('Task canceled' in log_msg)
        task_status = TaskStatusManager.find_by_task_id(task_id)
        self.assertEqual(task_status['state'], CALL_CANCELED_STATE)

    @mock.patch('pulp.server.async.tasks.controller.revoke', autospec=True)
    @mock.patch('pulp.server.async.tasks.logger', autospec=True)
    def test_cancel_after_task_finished(self, logger, revoke):
        """
        Test that canceling a task that is already finished results in no change
        to the task state.
        """
        task_id = '1234abcd'
        TaskStatusManager.create_task_status(task_id, 'test_worker', state=CALL_FINISHED_STATE)

        tasks.cancel(task_id)
        task_status = TaskStatusManager.find_by_task_id(task_id)
        self.assertEqual(task_status['state'], CALL_FINISHED_STATE)

    @mock.patch('pulp.server.async.tasks.controller.revoke', autospec=True)
    @mock.patch('pulp.server.async.tasks.logger', autospec=True)
    def test_cancel_after_task_canceled(self, *unused_mocks):
        """
        Test that canceling a task that was already canceled results in no change
        to the task state.
        """
        task_id = '1234abcd'
        TaskStatusManager.create_task_status(task_id, 'test_worker', state=CALL_CANCELED_STATE)

        tasks.cancel(task_id)
        task_status = TaskStatusManager.find_by_task_id(task_id)
        self.assertEqual(task_status['state'], CALL_CANCELED_STATE)


class TestRegisterSigtermHandler(unittest.TestCase):
    """
    Test the register_sigterm_handler() decorator.
    """
    def test_error_case(self):
        """
        Make sure that register_sigterm_handler() does the right thing during the error case.
        """
        class FakeException(Exception):
            """
            This Exception gets raised by f(). It's better to raise this instead of Exception, so we
            can assert it with self.assertRaises without missing the Exceptions that could be raised
            by the other assertions in f().
            """

        def f(*args, **kwargs):
            """
            This function will be wrapped by the decorator during this test. It asserts that the
            signal handler is correct and then raises Exception.

            :param args:   positional arguments that will be asserted to be correct
            :type  args:   tuple
            :param kwargs: keyword argumets that will be asserted to be correct
            :type  kwargs: dict
            """
            # Make sure the correct params were passed
            self.assertEqual(args, some_args)
            self.assertEqual(kwargs, some_kwargs)
            # We can't assert that our mock cancel method below is the handler, because the real
            # handler is the cancel inside of register_sigterm_handler. What we can do is to assert
            # that the signal handler has changed, and that calling the signal handler calls our
            # mock cancel.
            signal_handler = signal.getsignal(signal.SIGTERM)
            self.assertNotEqual(signal_handler, starting_term_handler)
            # Now let's call the signal handler and make sure that cancel() gets called.
            self.assertEqual(cancel.call_count, 0)
            signal_handler(signal.SIGTERM, None)
            self.assertEqual(cancel.call_count, 1)

            raise FakeException()

        f = mock.MagicMock(side_effect=f)
        cancel = mock.MagicMock()
        starting_term_handler = signal.getsignal(signal.SIGTERM)
        wrapped_f = tasks.register_sigterm_handler(f, cancel)
        # So far, the signal handler should still be the starting one
        self.assertEqual(signal.getsignal(signal.SIGTERM), starting_term_handler)
        some_args = (1, 'b', 4)
        some_kwargs = {'key': 'value'}

        # Now, let's call wrapped_f(). This should raise the Exception, but the signal handler
        # should be restored to its initial value. f() also asserts that during the operation the
        # signal handler is cancel.
        self.assertRaises(FakeException, wrapped_f, *some_args, **some_kwargs)

        # Assert that f() was called with the right params
        f.assert_called_once_with(*some_args, **some_kwargs)
        # Assert that the signal handler has been restored
        self.assertEqual(signal.getsignal(signal.SIGTERM), starting_term_handler)

    def test_normal_case(self):
        """
        Make sure that register_sigterm_handler() does the right thing during the normal case.
        """
        def f(*args, **kwargs):
            """
            This function will be wrapped by the decorator during this test. It asserts that the
            signal handler is correct and then returns 42.
            """
            self.assertEqual(args, some_args)
            self.assertEqual(kwargs, some_kwargs)
            # We can't assert that our mock cancel method below is the handler, because the real
            # handler is the cancel inside of register_sigterm_handler. What we can do is to assert
            # that the signal handler has changed, and that calling the signal handler calls our
            # mock cancel.
            signal_handler = signal.getsignal(signal.SIGTERM)
            self.assertNotEqual(signal_handler, starting_term_handler)
            # Now let's call the signal handler and make sure that cancel() gets called.
            self.assertEqual(cancel.call_count, 0)
            signal_handler(signal.SIGTERM, None)
            self.assertEqual(cancel.call_count, 1)

            return 42

        f = mock.MagicMock(side_effect=f)
        cancel = mock.MagicMock()
        starting_term_handler = signal.getsignal(signal.SIGTERM)
        wrapped_f = tasks.register_sigterm_handler(f, cancel)
        # So far, the signal handler should still be the starting one
        self.assertEqual(signal.getsignal(signal.SIGTERM), starting_term_handler)
        some_args = (1, 'b', 4)
        some_kwargs = {'key': 'value'}

        # Now, let's call wrapped_f(). This should raise the Exception, but the signal handler
        # should be restored to its initial value. f() also asserts that during the operation the
        # signal handler is cancel.
        return_value = wrapped_f(*some_args, **some_kwargs)

        self.assertEqual(return_value, 42)
        # Assert that f() was called with the right params
        f.assert_called_once_with(*some_args, **some_kwargs)
        # Assert that the signal handler has been restored
        self.assertEqual(signal.getsignal(signal.SIGTERM), starting_term_handler)


class TestGetCurrentTaskId(unittest.TestCase):

    @mock.patch('pulp.server.async.tasks.current_task')
    def test_get_task_id(self, mock_current_task):
        mock_current_task.request.id = 'foo'
        self.assertEquals('foo', tasks.get_current_task_id())

    def test_get_task_id_not_in_task(self):
        self.assertEquals(None, tasks.get_current_task_id())


class TestCleanupOldWorker(unittest.TestCase):

    @mock.patch('pulp.server.async.tasks._delete_worker')
    def test_assert_calls__delete_worker_synchronously(self, mock__delete_worker):
        sender = mock.Mock()
        tasks.cleanup_old_worker(sender=sender)
        mock__delete_worker.assert_called_once_with(sender.hostname, normal_shutdown=True)


class TestScheduledTasks(unittest.TestCase):

    @mock.patch('pulp.server.db.reaper.reap_expired_documents.apply_async')
    def test_reap_expired_documents_apply_async(self, mock_reaper_apply_async):
        queue_reap_expired_documents()
        mock_reaper_apply_async.assert_called_once_with(tags=[action_tag('reaper')])

    @mock.patch('pulp.server.maintenance.monthly.monthly_maintenance.apply_async')
    def test_monthly_maintenance_apply_async(self, mock_monthly_apply_async):
        queue_monthly_maintenance()
        mock_monthly_apply_async.assert_called_once_with(tags=[action_tag('monthly')])