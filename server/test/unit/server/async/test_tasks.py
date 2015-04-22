"""
This module contains tests for the pulp.server.async.tasks module.
"""
from datetime import datetime
import signal
import time
import unittest
import uuid

from celery.app import defaults
from celery.result import AsyncResult
import celery
import mock

from ...base import PulpServerTests, ResourceReservationTests
from pulp.common import dateutils
from pulp.common.constants import (CALL_CANCELED_STATE, CALL_FINISHED_STATE,
                                   CALL_RUNNING_STATE, CALL_WAITING_STATE)
from pulp.devel.unit.util import compare_dict
from pulp.server.exceptions import PulpException
from pulp.server.async import tasks, worker_watcher
from pulp.server.async.task_status_manager import TaskStatusManager
from pulp.server.db.model.dispatch import TaskStatus
from pulp.server.db.model.resources import Worker, ReservedResource


# Worker names
WORKER_1 = 'worker-1'
WORKER_2 = 'worker-2'
WORKER_3 = 'worker-3'
# Worker queue names
WORKER_1_QUEUE = '%s.dq' % WORKER_1
WORKER_2_QUEUE = '%s.dq' % WORKER_2
WORKER_3_QUEUE = '%s.dq' % WORKER_3


class TestDeleteWorker(ResourceReservationTests):
    """
    Test the _delete_worker() Task.
    """
    @mock.patch('pulp.server.async.tasks.controller.add_consumer')
    @mock.patch('pulp.server.async.tasks.cancel')
    @mock.patch('pulp.server.async.tasks.logger')
    def test__delete_worker(self, logger, cancel, mock_add_consumer):
        """
        Assert that the correct Tasks get canceled when their Worker is deleted, and that the Worker
        is removed from the database.
        """
        # cause two workers to be added to the database as having workers
        worker_watcher.handle_worker_heartbeat({
            'timestamp': time.time(),
            'type': 'worker-heartbeat',
            'hostname': WORKER_1,
        })
        worker_watcher.handle_worker_heartbeat({
            'timestamp': time.time(),
            'type': 'worker-heartbeat',
            'hostname': WORKER_2,
        })
        # Let's simulate three tasks being assigned to WORKER_2, with two of them being
        # in an incomplete state and one in a complete state. We will delete WORKER_2,
        # which should cause the two to get canceled. Let's put task_1 in progress
        TaskStatusManager.create_task_status('task_1', WORKER_2_QUEUE,
                                             state=CALL_RUNNING_STATE)
        TaskStatusManager.create_task_status('task_2', WORKER_2_QUEUE,
                                             state=CALL_WAITING_STATE)
        # This task shouldn't get canceled because it isn't in an incomplete state
        TaskStatusManager.create_task_status('task_3', WORKER_2_QUEUE,
                                             state=CALL_FINISHED_STATE)
        # Let's make a task in a worker that is still present just to make sure it isn't touched.
        TaskStatusManager.create_task_status('task_4', WORKER_1_QUEUE,
                                             state=CALL_RUNNING_STATE)

        # Let's just make sure the setup worked and that we have a Worker with RR2
        worker_collection = Worker.get_collection()
        self.assertEqual(worker_collection.find({'_id': WORKER_2}).count(), 1)

        # Now let's delete the Worker named WORKER_2
        tasks._delete_worker.apply_async(args=(WORKER_2,),
                                         queue=tasks.RESOURCE_MANAGER_QUEUE)

        # cancel() should have been called twice with task_1 and task_2 as parameters
        self.assertEqual(cancel.call_count, 2)
        # Let's build a set out of the two times that cancel was called. We can't know for sure
        # which order the Tasks got canceled in, but we can assert that the correct two tasks were
        # canceled (task_3 should not appear in this set).
        cancel_param_set = set([c[1] for c in cancel.mock_calls])
        self.assertEqual(cancel_param_set, set([('task_1',), ('task_2',)]))
        # We should have logged that we are canceling the tasks
        self.assertEqual(logger.call_count, 0)
        self.assertTrue(WORKER_2 in logger.mock_calls[0][1][0])
        self.assertTrue('Canceling the tasks' in logger.mock_calls[0][1][0])

        # The Worker should have been deleted
        self.assertEqual(worker_collection.find({'_id': WORKER_2}).count(), 0)
        # the Worker for RW1 should remain
        self.assertEqual(worker_collection.find({'_id': WORKER_1}).count(), 1)

    def test__delete_worker_no_database_entry(self):
        """
        Call _delete_worker() with a Worker that is not in the database. _delete_worker() relies on
        the database information, so it should return without error when called in this way.
        """
        try:
            tasks._delete_worker('does not exist Worker name')
        except Exception:
            self.fail('_delete_worker() on a Worker that is not in the database caused an '
                      'Exception')

    @mock.patch('pulp.server.async.tasks._')
    @mock.patch('pulp.server.async.tasks.logger')
    def test__delete_worker_normal_shutdown_true(self, mock_logger, mock_underscore):
        """
        Call _delete_worker() with the normal_shutdown keyword argument set to True. This should
        not make any calls to _() or logger().
        """
        tasks._delete_worker('does not exist Worker name')
        self.assertTrue(not mock_underscore.called)
        self.assertTrue(not mock_logger.called)


class TestQueueReleaseResource(ResourceReservationTests):
    """
    Test the _queue_release_resource() function.
    """
    @mock.patch('pulp.server.async.tasks._release_resource')
    def test__queue_release_resource(self, _release_resource):
        """
        Make sure that _queue_release_resource queues _release_resource with the correct resource_id
        in the resource manager's queue.
        """
        resource_id = 'some_resource'

        tasks._queue_release_resource.apply_async((resource_id,), queue='some_queue')

        _release_resource.apply_async.assert_called_once_with(args=(resource_id,),
                                                              queue=tasks.RESOURCE_MANAGER_QUEUE)


class TestReleaseResource(ResourceReservationTests):
    """
    Test the _release_resource() Task.
    """
    def test__release_resource_not_in__resource_map(self):
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
        reserved_resource_1 = ReservedResource('resource_1', worker_1.name, 7)
        reserved_resource_1.save()
        reserved_resource_2 = ReservedResource('resource_2', worker_2.name, 3)
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
        rr_1 = rrc.find_one({'_id': reserved_resource_1.name})
        self.assertEqual(rr_1['assigned_queue'], reserved_resource_1.assigned_queue)
        self.assertEqual(rr_1['num_reservations'], 7)
        rr_2 = rrc.find_one({'_id': reserved_resource_2.name})
        self.assertEqual(rr_2['assigned_queue'], reserved_resource_2.assigned_queue)
        self.assertEqual(rr_2['num_reservations'], 3)

    def test__release_resource_task_count_one(self):
        """
        Test _release_resource() with a resource that has a task count of one. This should remove
        the resource from the database.
        """
        # Set up two workers
        now = datetime.utcnow()
        worker_1 = Worker(WORKER_1, now)
        worker_1.save()
        worker_2 = Worker(WORKER_2, now)
        worker_2.save()
        # Set up two reserved resources
        reserved_resource_1 = ReservedResource('resource_1', worker_1.name, 7)
        reserved_resource_1.save()
        reserved_resource_2 = ReservedResource('resource_2', worker_2.name, 1)
        reserved_resource_2.save()

        # This should remove resource_2 from the _resource_map.
        tasks._release_resource('resource_2')

        # resource_2 should have been removed from the database
        rrc = ReservedResource.get_collection()
        self.assertEqual(rrc.count(), 1)
        rr_1 = rrc.find_one({'_id': reserved_resource_1.name})
        self.assertEqual(rr_1['assigned_queue'], reserved_resource_1.assigned_queue)
        self.assertEqual(rr_1['num_reservations'], 7)

    def test__release_resource_task_count_two(self):
        """
        Test _release_resource() with a resource that has a task count of two. This should simply
        decrement the task_count for the resource, but should not remove it from the database.
        """
        # Set up two workers
        now = datetime.utcnow()
        worker_1 = Worker(WORKER_1, now)
        worker_1.save()
        worker_2 = Worker(WORKER_2, now)
        worker_2.save()
        # Set up two resource reservations, using our workers from above
        reserved_resource_1 = ReservedResource('resource_1', worker_1.name, 7)
        reserved_resource_1.save()
        reserved_resource_2 = ReservedResource('resource_2', worker_2.name, 2)
        reserved_resource_2.save()

        # This should reduce the reserved_resource_2 num_reservations to 1.
        tasks._release_resource('resource_2')

        # Make sure the ReservedResources are also correct
        rrc = ReservedResource.get_collection()
        self.assertEqual(rrc.count(), 2)
        rr_1 = rrc.find_one({'_id': reserved_resource_1.name})
        self.assertEqual(rr_1['assigned_queue'], reserved_resource_1.assigned_queue)
        self.assertEqual(rr_1['num_reservations'], 7)
        rr_2 = rrc.find_one({'_id': reserved_resource_2.name})
        self.assertEqual(rr_2['assigned_queue'], reserved_resource_2.assigned_queue)
        self.assertEqual(rr_2['num_reservations'], 1)


class TestReserveResource(ResourceReservationTests):
    """
    Test the _reserve_resource() Task.
    """
    def test__reserve_resource_with_existing_reservation(self):
        """
        Test _reserve_resource() with a resource that has an existing reservation in the database.
        It should return the queue listed in the database, and increment the reservation counter.
        """
        # Set up a worker with a reservation count of 1
        now = datetime.utcnow()
        worker_1 = Worker(WORKER_1, now)
        worker_1.save()
        # Set up a resource reservation, using our worker from above
        reserved_resource_1 = ReservedResource('resource_1', worker_1.queue_name, 1)
        reserved_resource_1.save()

        # This should increase the reserved_resource_1 num_reservations to 2. worker_1's name should
        # be returned
        queue = tasks._reserve_resource('resource_1')

        self.assertEqual(queue, WORKER_1_QUEUE)
        # Make sure the ReservedResource is correct
        rrc = ReservedResource.get_collection()
        self.assertEqual(rrc.count(), 1)
        rr_1 = rrc.find_one({'_id': reserved_resource_1.name})
        self.assertEqual(rr_1['assigned_queue'], WORKER_1_QUEUE)
        self.assertEqual(rr_1['num_reservations'], 2)

    def test__reserve_resource_without_existing_reservation(self):
        """
        Test _reserve_resource() with a resource that does not have an existing reservation in the
        database. It should find the least busy worker, add a reservation to the database with that
        worker's queue, and then return the queue name.
        """
        # Set up a worker
        worker_1 = Worker(WORKER_1, datetime.utcnow())
        worker_1.save()

        queue = tasks._reserve_resource('resource_1')

        self.assertEqual(queue, WORKER_1_QUEUE)
        # Make sure the ReservedResource is correct
        rrc = ReservedResource.get_collection()
        self.assertEqual(rrc.count(), 1)
        rr_1 = rrc.find_one({'_id': 'resource_1'})
        self.assertEqual(rr_1['assigned_queue'], WORKER_1_QUEUE)
        self.assertEqual(rr_1['num_reservations'], 1)


def _reserve_resource_apply_async():
    class MockAsyncResult(object):
        def get(self):
            return WORKER_1_QUEUE
    return MockAsyncResult()


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


class TestTask(ResourceReservationTests):
    """
    Test the pulp.server.tasks.Task class.
    """
    @mock.patch('pulp.server.async.tasks._queue_release_resource')
    @mock.patch('pulp.server.async.tasks._reserve_resource.apply_async',
                return_value=_reserve_resource_apply_async())
    @mock.patch('pulp.server.async.tasks.Task.apply_async', autospec=True)
    def test_apply_async_with_reservation_calls_apply_async(
            self, apply_async, _reserve_resource, _queue_release_resource):
        """
        Assert that apply_async_with_reservation() calls Celery's apply_async.
        """
        class MockAsyncResult(object):
            def __init__(self):
                self.id = 'some_task_id'
        # Let's make up the return value from Celery
        mock_async_result = MockAsyncResult()
        apply_async.return_value = mock_async_result
        some_args = [1, 'b', 'iii']
        some_kwargs = {'1': 'for the money', '2': 'for the show', 'queue': WORKER_1_QUEUE,
                       'exchange': 'C.dq'}
        resource_id = 'three_to_get_ready'
        resource_type = 'reserve_me'
        task = tasks.Task()

        async_result = task.apply_async_with_reservation(resource_type, resource_id,
                                                         *some_args, **some_kwargs)

        self.assertEqual(async_result, mock_async_result)
        expected_resource_id = ":".join([resource_type, resource_id])
        _reserve_resource.assert_called_once_with((expected_resource_id,),
                                                  queue=tasks.RESOURCE_MANAGER_QUEUE)
        apply_async.assert_called_once_with(task, *some_args, **some_kwargs)
        _queue_release_resource.apply_async.assert_called_once_with((expected_resource_id,),
                                                                    queue=WORKER_1,
                                                                    exchange='C.dq')

    @mock.patch('pulp.server.async.tasks.Task.request')
    def test_on_success_handler(self, mock_request):
        """
        Make sure that overridden on_success handler updates task status correctly
        """
        retval = 'random_return_value'
        task_id = str(uuid.uuid4())
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'queue': WORKER_2_QUEUE}
        mock_request.called_directly = False

        task_status = TaskStatusManager.create_task_status(task_id, 'some_queue')
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
    def test_on_success_handler_spawned_task_status(self, mock_request):
        """
        Make sure that overridden on_success handler updates task status correctly
        """
        async_result = AsyncResult('foo-id')

        retval = tasks.TaskResult(error=PulpException('error-foo'),
                                  result='bar')
        retval.spawned_tasks = [async_result]

        task_id = str(uuid.uuid4())
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'queue': WORKER_2_QUEUE}
        mock_request.called_directly = False

        task_status = TaskStatusManager.create_task_status(task_id, 'some_queue')
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
    def test_on_success_handler_spawned_task_dict(self, mock_request):
        """
        Make sure that overridden on_success handler updates task status correctly
        """
        retval = tasks.TaskResult(spawned_tasks=[{'task_id': 'foo-id'}], result='bar')

        task_id = str(uuid.uuid4())
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'queue': WORKER_2_QUEUE}
        mock_request.called_directly = False

        task_status = TaskStatusManager.create_task_status(task_id, 'some_queue')
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
    def test_on_success_handler_async_result(self, mock_request):
        """
        Make sure that overridden on_success handler updates task status correctly
        """
        retval = AsyncResult('foo-id')

        task_id = str(uuid.uuid4())
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'queue': WORKER_2_QUEUE}
        mock_request.called_directly = False

        task_status = TaskStatusManager.create_task_status(task_id, 'some_queue')
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
    def test_on_success_with_canceled_task(self, mock_request):
        """
        Make sure on_success() does not move a canceled Task to 'finished' state.
        """
        retval = 'random_return_value'
        task_id = str(uuid.uuid4())
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'queue': WORKER_2_QUEUE}
        mock_request.called_directly = False
        task_status = TaskStatusManager.create_task_status(task_id, 'some_queue',
                                                           state=CALL_CANCELED_STATE)
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

    @mock.patch('pulp.server.async.tasks.Task.request')
    def test_on_failure_handler(self, mock_request):
        """
        Make sure that overridden on_failure handler updates task status correctly
        """
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

        task_status = TaskStatusManager.create_task_status(task_id, 'some_queue')
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

    @mock.patch('celery.Task.apply_async')
    def test_apply_async_task_status(self, apply_async):
        """
        Assert that apply_async() creates new task status.
        """
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'queue': WORKER_1_QUEUE}
        apply_async.return_value = celery.result.AsyncResult('test_task_id')
        task = tasks.Task()

        task.apply_async(*args, **kwargs)

        task_statuses = list(TaskStatusManager.find_all())
        self.assertEqual(len(task_statuses), 1)
        new_task_status = task_statuses[0]
        self.assertEqual(new_task_status['task_id'], 'test_task_id')
        self.assertEqual(new_task_status['queue'], WORKER_1_QUEUE)
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
    def test_apply_async_task_status_default_queue(self, apply_async):
        """
        Assert that apply_async() creates new task status when we do not pass the queue kwarg. It
        default to the default Celery queue.
        """
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags']}
        apply_async.return_value = celery.result.AsyncResult('test_task_id')
        task = tasks.Task()

        task.apply_async(*args, **kwargs)

        task_statuses = list(TaskStatusManager.find_all())
        self.assertEqual(len(task_statuses), 1)
        new_task_status = task_statuses[0]
        self.assertEqual(new_task_status['task_id'], 'test_task_id')
        self.assertEqual(new_task_status['queue'],
                         defaults.NAMESPACES['CELERY']['DEFAULT_QUEUE'].default)
        self.assertEqual(new_task_status['tags'], kwargs['tags'])
        self.assertEqual(new_task_status['state'], 'waiting')

    @mock.patch('celery.Task.apply_async')
    def test_apply_async_queue_name_modified_if_exchange_eq_C_dq(self, apply_async):
        """
        Assert that apply_async() removes the .dq from the queue name in cases where the keyword
        'exchange' equals 'C.dq'. This queue name modification is asserted by the call to
        apply_async() on the parent. Also asserts that the actual queue name (with the .dq) is
        saved on the created TaskStatus object.
        """
        args = [1, 'b', 'iii']
        kwargs = {'queue': 'worker-prod.dq', 'tags': ['test_tags'], 'exchange': 'C.dq'}
        apply_async.return_value = celery.result.AsyncResult('test_task_id')
        task = tasks.Task()

        task.apply_async(*args, **kwargs)

        apply_async.assert_called_once_with(*args, queue='worker-prod', exchange='C.dq')

        task_statuses = list(TaskStatusManager.find_all())
        self.assertEqual(len(task_statuses), 1)
        new_task_status = task_statuses[0]
        self.assertEqual(new_task_status['task_id'], 'test_task_id')
        self.assertEqual(new_task_status['queue'], 'worker-prod.dq')
        self.assertEqual(new_task_status['tags'], kwargs['tags'])
        self.assertEqual(new_task_status['state'], 'waiting')

    @mock.patch('celery.Task.apply_async')
    def test_apply_async_queue_name_modified_if_exchange_present_but_neq_C_dq(self, apply_async):
        """
        Assert that apply_async() does not adjust the queue name or exchange name in cases where
        the keyword 'exchange' is present, but not equal to 'C.dq'. Also asserts that the
        unmodified queue name is saved on the created TaskStatus object.
        """
        args = [1, 'b', 'iii']
        kwargs = {'queue': 'worker-prod.dq', 'tags': ['test_tags'], 'exchange': 'foobar'}
        apply_async.return_value = celery.result.AsyncResult('test_task_id')
        task = tasks.Task()

        task.apply_async(*args, **kwargs)

        apply_async.assert_called_once_with(*args, queue='worker-prod.dq', exchange='foobar')

        task_statuses = list(TaskStatusManager.find_all())
        self.assertEqual(len(task_statuses), 1)
        new_task_status = task_statuses[0]
        self.assertEqual(new_task_status['task_id'], 'test_task_id')
        self.assertEqual(new_task_status['queue'], 'worker-prod.dq')
        self.assertEqual(new_task_status['tags'], kwargs['tags'])
        self.assertEqual(new_task_status['state'], 'waiting')

    @mock.patch('celery.Task.apply_async')
    def test_apply_async_task_canceled(self, apply_async):
        """
        Assert that apply_async() honors 'canceled' task status.
        """
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags']}
        task_id = 'test_task_id'
        now = datetime.utcnow()
        TaskStatusManager.create_task_status(task_id, Worker('test-worker', now),
                                             state=CALL_CANCELED_STATE)
        apply_async.return_value = celery.result.AsyncResult(task_id)

        task = tasks.Task()
        task.apply_async(*args, **kwargs)

        task_status = TaskStatusManager.find_by_task_id(task_id)
        self.assertEqual(task_status['state'], 'canceled')
        self.assertEqual(task_status['start_time'], None)


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
        now = datetime.utcnow()
        test_worker = Worker('test_worker', now)
        TaskStatusManager.create_task_status(task_id, test_worker.name)
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
        now = datetime.utcnow()
        test_worker = Worker('test_worker', now)
        TaskStatusManager.create_task_status(task_id, test_worker.name, state=CALL_FINISHED_STATE)

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
        now = datetime.utcnow()
        test_worker = Worker('test_worker', now)
        TaskStatusManager.create_task_status(task_id, test_worker.name, state=CALL_CANCELED_STATE)

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


class TestCleanupOldWorker (unittest.TestCase):

    @mock.patch('pulp.server.async.tasks._delete_worker')
    def test_assert_calls__delete_worker_synchronously(self, mock__delete_worker):
        sender = mock.Mock()
        tasks.cleanup_old_worker(sender=sender)
        mock__delete_worker.assert_called_once_with(sender.hostname, normal_shutdown=True)
