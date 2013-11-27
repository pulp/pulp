# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
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
This module contains tests for the pulp.server.tasks module.
"""
from copy import deepcopy
import uuid

import celery
import mock

from ...base import PulpServerTests, ResourceReservationTests
from pulp.server.async import tasks
from pulp.server.async.task_status_manager import TaskStatusManager
from pulp.server.db.model.dispatch import TaskStatus
from pulp.server.db.model.resources import AvailableQueue, ReservedResource


RESERVED_WORKER_1 = '%s1' % tasks.RESERVED_WORKER_NAME_PREFIX
RESERVED_WORKER_2 = '%s2' % tasks.RESERVED_WORKER_NAME_PREFIX
RESERVED_WORKER_3 = '%s3' % tasks.RESERVED_WORKER_NAME_PREFIX
# This is used as the mock return value for the celery.app.control.Inspect.active_queues() method
MOCK_ACTIVE_QUEUES_RETURN_VALUE = {
    # This is a plain old default Celery worker, subscribed to the general Celery queue
    u'worker_1': [
        {u'exclusive': False, u'name': u'celery', u'exchange': {
            u'name': u'celery', u'durable': True, u'delivery_mode': 2, u'passive': False,
            u'arguments': None, u'type': u'direct', u'auto_delete': False},
         u'durable': True, u'routing_key': u'celery', u'no_ack': False, u'alias': None,
         u'queue_arguments': None, u'binding_arguments': None, u'bindings': [],
         u'auto_delete': False}],
    # This is a worker subscribed only to a reserved resource queue on worker_1
    RESERVED_WORKER_1: [
        {u'exclusive': False, u'name': RESERVED_WORKER_1, u'exchange': {
            u'name': RESERVED_WORKER_1, u'durable': True,
            u'delivery_mode': 2, u'passive': False, u'arguments': None, u'type': u'direct',
            u'auto_delete': False},
         u'durable': True, u'routing_key': RESERVED_WORKER_1, u'no_ack': False,
         u'alias': None, u'queue_arguments': None, u'binding_arguments': None, u'bindings': [],
         u'auto_delete': False}],
    # This is a worker subscribed to both a reserved resource queue and the general Celery queue
    RESERVED_WORKER_2: [
        {u'exclusive': False, u'name': RESERVED_WORKER_2, u'exchange': {
            u'name': RESERVED_WORKER_2, u'durable': True,
            u'delivery_mode': 2, u'passive': False, u'arguments': None, u'type': u'direct',
            u'auto_delete': False},
         u'durable': True, u'routing_key': RESERVED_WORKER_2, u'no_ack': False,
         u'alias': None, u'queue_arguments': None, u'binding_arguments': None, u'bindings': [],
         u'auto_delete': False},
        {u'exclusive': False, u'name': u'celery', u'exchange': {
            u'name': u'celery', u'durable': True, u'delivery_mode': 2, u'passive': False,
            u'arguments': None, u'type': u'direct', u'auto_delete': False},
         u'durable': True, u'routing_key': u'celery', u'no_ack': False, u'alias': None,
         u'queue_arguments': None, u'binding_arguments': None, u'bindings': [],
         u'auto_delete': False}],
    # This is another worker, but it is not yet subscribed to any queues
    RESERVED_WORKER_3: [],
    # This is a worker subscribed to the special ReservationManager queue
    u'resource_manager': [
        {u'exclusive': False, u'name': u'resource_manager', u'exchange': {
            u'name': u'resource_manager', u'durable': True, u'delivery_mode': 2, u'passive': False,
            u'arguments': None, u'type': u'direct', u'auto_delete': False},
         u'durable': True, u'routing_key': u'resource_manager', u'no_ack': False, u'alias': None,
         u'queue_arguments': None, u'binding_arguments': None, u'bindings': [],
         u'auto_delete': False}]}


class TestBabysit(ResourceReservationTests):
    """
    Test the babysit() function.
    """
    @mock.patch('celery.app.control.Inspect.active_queues',
                return_value=MOCK_ACTIVE_QUEUES_RETURN_VALUE)
    @mock.patch('pulp.server.async.tasks.controller.add_consumer')
    def test_babysit_creates_correct_records(self, add_consumer, active_queues):
        """
        Test babysit() with a blank database. It should create the correct AvailableQueues.
        """
        tasks.babysit()

        # babysit() should have called the active_queues() method
        active_queues.assert_called_once_with()
        # There should be three ActiveQueues, one for each reserved worker in the mock data
        aqc = AvailableQueue.get_collection()
        self.assertEqual(aqc.count(), 3)
        # Let's make sure their names and num_reservations counts are correct
        self.assertEqual(aqc.find_one({'_id': RESERVED_WORKER_1})['num_reservations'], 0)
        self.assertEqual(aqc.find_one({'_id': RESERVED_WORKER_2})['num_reservations'], 0)
        self.assertEqual(aqc.find_one({'_id': RESERVED_WORKER_3})['num_reservations'], 0)
        # Reserved worker 3 wasn't assigned to a queue, so babysit() should have assigned it to one
        add_consumer.assert_called_once_with(queue=RESERVED_WORKER_3,
                                             destination=(RESERVED_WORKER_3,))

    @mock.patch('celery.app.control.Inspect.active_queues',
                return_value=MOCK_ACTIVE_QUEUES_RETURN_VALUE)
    @mock.patch('pulp.server.async.tasks.controller.add_consumer')
    def test_babysit_deletes_correct_records(self, add_consumer, active_queues):
        """
        Test babysit() with pre-existing state. It should create the correct AvailableQueues, and
        delete other ones, and leave others in place.
        """
        # This AvailableQueue should remain in the DB
        available_queue_2 = AvailableQueue(name=RESERVED_WORKER_2)
        available_queue_2.save()
        # This AvailableQueue doesn't exist anymore since it's not in the mock results, so it should
        # get deleted
        available_queue_4 = AvailableQueue(name='%s4' % tasks.RESERVED_WORKER_NAME_PREFIX)
        available_queue_4.save()

        tasks.babysit()

        # babysit() should have called the active_queues() method
        active_queues.assert_called_once_with()
        # There should be three ActiveQueues, one for each reserved worker in the mock data
        aqc = AvailableQueue.get_collection()
        self.assertEqual(aqc.count(), 3)
        # Let's make sure their names and num_reservations counts are correct
        self.assertEqual(aqc.find_one({'_id': RESERVED_WORKER_1})['num_reservations'], 0)
        self.assertEqual(aqc.find_one({'_id': RESERVED_WORKER_2})['num_reservations'], 0)
        self.assertEqual(aqc.find_one({'_id': RESERVED_WORKER_3})['num_reservations'], 0)
        # Reserved worker 3 wasn't assigned to a queue, so babysit() should have assigned it to one
        add_consumer.assert_called_once_with(queue=RESERVED_WORKER_3,
                                             destination=(RESERVED_WORKER_3,))


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
        # Set up two available queues
        available_queue_1 = AvailableQueue(RESERVED_WORKER_1, 7)
        available_queue_1.save()
        available_queue_2 = AvailableQueue(RESERVED_WORKER_2, 3)
        available_queue_2.save()
        # Set up two resource reservations, using our available_queues from above
        reserved_resource_1 = ReservedResource('resource_1', available_queue_1.name,
                                               available_queue_1.num_reservations)
        reserved_resource_1.save()
        reserved_resource_2 = ReservedResource('resource_2', available_queue_2.name,
                                               available_queue_2.num_reservations)
        reserved_resource_2.save()

        # This should not raise any Exception, but should also not alter either the AvailableQueue
        # collection or the ReservedResource collection
        tasks._release_resource('made_up_resource_id')

        # Make sure that the available queues collection has not been altered
        aqc = AvailableQueue.get_collection()
        self.assertEqual(aqc.count(), 2)
        aq_1 = aqc.find_one({'_id': available_queue_1.name})
        self.assertEqual(aq_1['num_reservations'], 7)
        aq_2 = aqc.find_one({'_id': available_queue_2.name})
        self.assertEqual(aq_2['num_reservations'], 3)
        # Make sure that the reserved resources collection has not been altered
        rrc = ReservedResource.get_collection()
        self.assertEqual(rrc.count(), 2)
        rr_1 = rrc.find_one({'_id': reserved_resource_1.name})
        self.assertEqual(rr_1['assigned_queue'], reserved_resource_1.assigned_queue)
        self.assertEqual(rr_1['num_reservations'], 7)
        rr_2 = rrc.find_one({'_id': reserved_resource_2.name})
        self.assertEqual(rr_2['assigned_queue'], reserved_resource_2.assigned_queue)
        self.assertEqual(rr_2['num_reservations'], 3)

    def test__release_resource_queue_task_count_zero(self):
        """
        Test _release_resource() with a resource that has a queue with a task count of zero. This
        should not decrement the queue task count into the negative range.
        """
        # Set up two available queues, the second with a task count of 0
        available_queue_1 = AvailableQueue(RESERVED_WORKER_1, 7)
        available_queue_1.save()
        available_queue_2 = AvailableQueue(RESERVED_WORKER_2, 0)
        available_queue_2.save()
        # Set up two reserved resources, and let's make it so the second one is out of sync with its
        # queue's task count by setting its num_reservations to 1
        reserved_resource_1 = ReservedResource('resource_1', available_queue_1.name,
                                               available_queue_1.num_reservations)
        reserved_resource_1.save()
        reserved_resource_2 = ReservedResource('resource_2', available_queue_2.name, 1)
        reserved_resource_2.save()

        # This should remove resource_2 from the _resource_map, but should leave the queue's task
        # count at 0.
        tasks._release_resource('resource_2')

        # The _available_queue_task_counts should remain as they were before, since we don't want
        # queue lengths below zero
        aqc = AvailableQueue.get_collection()
        self.assertEqual(aqc.count(), 2)
        aq_1 = aqc.find_one({'_id': available_queue_1.name})
        self.assertEqual(aq_1['num_reservations'], 7)
        aq_2 = aqc.find_one({'_id': available_queue_2.name})
        self.assertEqual(aq_2['num_reservations'], 0)
        # resource_2 should have been removed from the database
        rrc = ReservedResource.get_collection()
        self.assertEqual(rrc.count(), 1)
        rr_1 = rrc.find_one({'_id': reserved_resource_1.name})
        self.assertEqual(rr_1['assigned_queue'], reserved_resource_1.assigned_queue)
        self.assertEqual(rr_1['num_reservations'], 7)

    def test__release_resource_task_count_one(self):
        """
        Test _release_resource() with a resource that has a task count of one. This should remove
        the resource from the database.
        """
        # Set up two available queues
        available_queue_1 = AvailableQueue(RESERVED_WORKER_1, 7)
        available_queue_1.save()
        available_queue_2 = AvailableQueue(RESERVED_WORKER_2, 1)
        available_queue_2.save()
        # Set up two reserved resources
        reserved_resource_1 = ReservedResource('resource_1', available_queue_1.name,
                                               available_queue_1.num_reservations)
        reserved_resource_1.save()
        reserved_resource_2 = ReservedResource('resource_2', available_queue_2.name,
                                               available_queue_2.num_reservations)
        reserved_resource_2.save()

        # This should remove resource_2 from the _resource_map, and should reduce the queue's task
        # count to 0.
        tasks._release_resource('resource_2')

        # available_queue_2 should have had its num_reservations reduced to 0, and the other one
        # should have remained the same
        aqc = AvailableQueue.get_collection()
        self.assertEqual(aqc.count(), 2)
        aq_1 = aqc.find_one({'_id': available_queue_1.name})
        self.assertEqual(aq_1['num_reservations'], 7)
        aq_2 = aqc.find_one({'_id': available_queue_2.name})
        self.assertEqual(aq_2['num_reservations'], 0)
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
        # Set up two available queues
        available_queue_1 = AvailableQueue(RESERVED_WORKER_1, 7)
        available_queue_1.save()
        available_queue_2 = AvailableQueue(RESERVED_WORKER_2, 2)
        available_queue_2.save()
        # Set up two resource reservations, using our available_queues from above
        reserved_resource_1 = ReservedResource('resource_1', available_queue_1.name,
                                               available_queue_1.num_reservations)
        reserved_resource_1.save()
        reserved_resource_2 = ReservedResource('resource_2', available_queue_2.name,
                                               available_queue_2.num_reservations)
        reserved_resource_2.save()

        # This should reduce the reserved_resource_2 num_reservations to 1, and should also reduce
        # available_queue_2's num_reservations to 1.
        tasks._release_resource('resource_2')

        # Make sure that the AvailableQueues are correct
        aqc = AvailableQueue.get_collection()
        self.assertEqual(aqc.count(), 2)
        aq_1 = aqc.find_one({'_id': available_queue_1.name})
        self.assertEqual(aq_1['num_reservations'], 7)
        aq_2 = aqc.find_one({'_id': available_queue_2.name})
        self.assertEqual(aq_2['num_reservations'], 1)
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
        # Set up an available queue with a reservation count of 1
        available_queue_1 = AvailableQueue(RESERVED_WORKER_1, 1)
        available_queue_1.save()
        # Set up a resource reservation, using our available_queue from above
        reserved_resource_1 = ReservedResource('resource_1', available_queue_1.name,
                                               available_queue_1.num_reservations)
        reserved_resource_1.save()

        # This should increase the reserved_resource_1 num_reservations to 2, and should also
        # increase available_queue_1's num_reservations to 2. available_queue_1's name should be
        # returned
        queue = tasks._reserve_resource('resource_1')

        self.assertEqual(queue, RESERVED_WORKER_1)
        # Make sure that the AvailableQueue is correct
        aqc = AvailableQueue.get_collection()
        self.assertEqual(aqc.count(), 1)
        aq_1 = aqc.find_one({'_id': available_queue_1.name})
        self.assertEqual(aq_1['num_reservations'], 2)
        # Make sure the ReservedResource is also correct
        rrc = ReservedResource.get_collection()
        self.assertEqual(rrc.count(), 1)
        rr_1 = rrc.find_one({'_id': reserved_resource_1.name})
        self.assertEqual(rr_1['assigned_queue'], RESERVED_WORKER_1)
        self.assertEqual(rr_1['num_reservations'], 2)

    def test__reserve_resource_without_existing_reservation(self):
        """
        Test _reserve_resource() with a resource that does not have an existing reservation in the
        database. It should find the least busy queue, add a reservation to the database with that
        queue, and then return the queue.
        """
        # Set up an available queue
        available_queue_1 = AvailableQueue(RESERVED_WORKER_1, 0)
        available_queue_1.save()

        queue = tasks._reserve_resource('resource_1')

        self.assertEqual(queue, RESERVED_WORKER_1)
        # Make sure that the AvailableQueue is correct
        aqc = AvailableQueue.get_collection()
        self.assertEqual(aqc.count(), 1)
        aq_1 = aqc.find_one({'_id': available_queue_1.name})
        self.assertEqual(aq_1['num_reservations'], 1)
        # Make sure the ReservedResource is also correct
        rrc = ReservedResource.get_collection()
        self.assertEqual(rrc.count(), 1)
        rr_1 = rrc.find_one({'_id': 'resource_1'})
        self.assertEqual(rr_1['assigned_queue'], RESERVED_WORKER_1)
        self.assertEqual(rr_1['num_reservations'], 1)


def _reserve_resource_apply_async():
    class AsyncResult(object):
        def get(self):
            return RESERVED_WORKER_1
    return AsyncResult()


class TestTask(PulpServerTests):
    """
    Test the pulp.server.tasks.Task class.
    """
    def clean(self):
        super(TestTask, self).clean()
        TaskStatus.get_collection().remove()

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
        some_kwargs = {'1': 'for the money', '2': 'for the show', 'queue': RESERVED_WORKER_1}
        resource_id = 'three_to_get_ready'
        task = tasks.Task()

        async_result = task.apply_async_with_reservation(resource_id, *some_args, **some_kwargs)

        self.assertEqual(async_result, mock_async_result)
        _reserve_resource.assert_called_once_with((resource_id,),
                                                  queue=tasks.RESOURCE_MANAGER_QUEUE)
        apply_async.assert_called_once_with(task, *some_args, **some_kwargs)
        _queue_release_resource.apply_async.assert_called_once_with((resource_id,),
                                                                    queue=RESERVED_WORKER_1)

    @mock.patch('pulp.server.async.tasks.Task.request')
    def test_on_success_handler(self, mock_request):
        """
        Make sure that overridden on_success handler updates task status correctly
        """
        retval = 'random_return_value'
        task_id = str(uuid.uuid4())
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'queue': RESERVED_WORKER_2}
        mock_request.called_directly = False

        task_status = TaskStatusManager.create_task_status(task_id)
        self.assertEqual(task_status['state'], None)
        self.assertEqual(task_status['finish_time'], None)

        task = tasks.Task()
        task.on_success(retval, task_id, args, kwargs)

        new_task_status = TaskStatusManager.find_by_task_id(task_id)
        self.assertEqual(new_task_status['state'], 'finished')
        self.assertEqual(new_task_status['result'], retval)
        self.assertFalse(new_task_status['finish_time'] == None)

    @mock.patch('pulp.server.async.tasks.Task.request')
    def test_on_failure_handler(self, mock_request):
        """
        Make sure that overridden on_failure handler updates task status correctly
        """
        exc = Exception()
        task_id = str(uuid.uuid4())
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags']}
        # on_failure handler expects an instance of celery's ExceptionInfo class
        # as one of the attributes. It stores string representation of traceback
        # in it's traceback instance variable. Creating a stub to imitate that behavior.
        class EInfo(object):
            def __init__(self):
                self.traceback = "string_repr_of_traceback"
        einfo = EInfo()
        mock_request.called_directly = False

        task_status = TaskStatusManager.create_task_status(task_id)
        self.assertEqual(task_status['state'], None)
        self.assertEqual(task_status['finish_time'], None)
        self.assertEqual(task_status['traceback'], None)

        task = tasks.Task()
        task.on_failure(exc, task_id, args, kwargs, einfo)

        new_task_status = TaskStatusManager.find_by_task_id(task_id)
        self.assertEqual(new_task_status['state'], 'error')
        self.assertFalse(new_task_status['finish_time'] == None)
        self.assertEqual(new_task_status['traceback'], einfo.traceback)

    @mock.patch('celery.Task.apply_async')
    def test_apply_async_task_status(self, apply_async):
        """
        Assert that apply_async() creates new task status.
        """
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'queue': RESERVED_WORKER_1}
        apply_async.return_value = celery.result.AsyncResult('test_task_id')

        task = tasks.Task()
        task.apply_async(*args, **kwargs)

        task_statuses = list(TaskStatusManager.find_all())
        self.assertEqual(len(task_statuses), 1)
        new_task_status = task_statuses[0]
        self.assertEqual(new_task_status['task_id'], 'test_task_id')
        self.assertEqual(new_task_status['tags'], kwargs['tags'])
        self.assertEqual(new_task_status['state'], 'waiting')


class TestCancel(PulpServerTests):
    """
    Test the tasks.cancel() function.
    """
    @mock.patch('pulp.server.async.tasks.controller.revoke', autospec=True)
    def test_cancel(self, revoke):
        task_id = '1234abcd'

        tasks.cancel(task_id)

        revoke.assert_called_once_with(task_id, terminate=True)
