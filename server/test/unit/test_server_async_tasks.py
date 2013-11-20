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

import mock

from base import PulpServerTests
from pulp.server.async import tasks
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


class ResourceReservationTests(PulpServerTests):
    def tearDown(self):
        AvailableQueue.get_collection().remove()
        ReservedResource.get_collection().remove()


class TestQueueReleaseResource(ResourceReservationTests):
    """
    Test the _queue_release_resource() function.
    """
    @mock.patch('pulp.server.async.tasks._release_resource')
    def test__queue_release_resource(self, _release_resource):
        """
        Make sure that _queue_release_resource queues _release_resource with the correct resource_id
        in the ResourceManager's queue.
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
        Test _release_resource() with a resource that is not in the _resource_map. This should be
        gracefully handled, and result in no changes to the _resource_map.
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
        # resource_2 should have been removed from the _resource_map
        rrc = ReservedResource.get_collection()
        self.assertEqual(rrc.count(), 1)
        rr_1 = rrc.find_one({'_id': reserved_resource_1.name})
        self.assertEqual(rr_1['assigned_queue'], reserved_resource_1.assigned_queue)
        self.assertEqual(rr_1['num_reservations'], 7)

    def test__release_resource_task_count_one(self):
        """
        Test _release_resource() with a resource that has a task count of one. This should remove
        the resource from the _resource_map.
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
        # resource_2 should have been removed from the _resource_map
        rrc = ReservedResource.get_collection()
        self.assertEqual(rrc.count(), 1)
        rr_1 = rrc.find_one({'_id': reserved_resource_1.name})
        self.assertEqual(rr_1['assigned_queue'], reserved_resource_1.assigned_queue)
        self.assertEqual(rr_1['num_reservations'], 7)

    def test__release_resource_task_count_two(self):
        """
        Test _release_resource() with a resource that has a task count of two. This should simply
        decrement the task_count for the resource, but should not remove it from the _resource_map.
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
        resource_manager = tasks.ResourceManager()
        resource_manager._resource_map = {
            'resource_1': {'queue': 'worker_1-reserved_1', 'task_count': 7},
            'resource_2': {'queue': 'worker_2-reserved_1', 'task_count': 3}}
        resource_manager._available_queue_task_counts = {'worker_1-reserved_1': 7,
                                                         'worker_2-reserved_1': 3}

        queue = resource_manager.reserve_resource('resource_3')

        self.assertEqual(queue, 'worker_2-reserved_1')
        # The available queue task count for worker_2-reserved_3 should have been incremented
        self.assertEqual(resource_manager._available_queue_task_counts,
                         {'worker_1-reserved_1': 7, 'worker_2-reserved_1': 4})
        # The _resource_map should now have a resource_3 entry with a task_count of 1 and the
        # correct queue
        self.assertEqual(
            resource_manager._resource_map,
            {'resource_1': {'queue': 'worker_1-reserved_1', 'task_count': 7},
             'resource_2': {'queue': 'worker_2-reserved_1', 'task_count': 3},
             'resource_3': {'queue': 'worker_2-reserved_1', 'task_count': 1}})


@mock.patch('celery.app.control.Inspect.active_queues',
            return_value=MOCK_ACTIVE_QUEUES_RETURN_VALUE)
class TestResourceManager(PulpServerTests):
    """
    Test the ResourceManager class.
    """
    def test___init__(self, active_queues):
        """
        Test the __init__() method.
        """
        resource_manager = tasks.ResourceManager()

        # There should be three available queues, all with their task counts initialized to 0
        self.assertEqual(
            resource_manager._available_queue_task_counts,
            {'worker_1-reserved_1': 0, 'worker_2-reserved_1': 0, 'worker_3-reserved_1': 0,
             'worker_3-reserved_2': 0})
        # There are three workers, and they collectively have four reserved task queues assigned to
        # them. Note that the celery and resource manager queues are not included here, as this data
        # structure should only contain information about reserved task queues.
        self.assertEqual(
            resource_manager._worker_queues,
            {'worker_1-reserved': ['worker_1-reserved_1'],
             'worker_2-reserved': ['worker_2-reserved_1'],
             'worker_3-reserved': ['worker_3-reserved_1', 'worker_3-reserved_2']})
        # Since no reservations have been made yet, the _resource_map attribute should be
        # initialized as an empty dictionary
        self.assertEqual(resource_manager._resource_map, {})

    def test__get_available_queue_no_queues_available(self, active_queues):
        """
        Test the _get_available_queue() method when there are no reserved queues available at all.
        It should raise a NoAvailableQueues Exception.
        """
        resource_manager = tasks.ResourceManager()
        # We can fake there being no available queues by setting the _available_queues_task_count to
        # the empty dictionary
        resource_manager._available_queue_task_counts = {}

        # When no queues are available, a NoAvailableQueues Exception should be raised
        self.assertRaises(tasks.NoAvailableQueues, resource_manager._get_available_queue)

    def test__get_available_queue_no_workers_available(self, active_queues):
        """
        Test the _get_available_queue() method when there are no workers assigned to reserved
        queues. It should raise a NoAvailableQueues Exception.
        """
        resource_manager = tasks.ResourceManager()
        # We can fake there being no workers assigned to queues by setting the _worker_queues to
        # the empty dictionary
        resource_manager._worker_queues = {}

        # When no queues are available, a NoAvailableQueues Exception should be raised
        self.assertRaises(tasks.NoAvailableQueues, resource_manager._get_available_queue)

    def test__get_available_queue_picks_least_busy_queue(self, active_queues):
        """
        Test that the _get_available_queue() method picks the least busy queue, when the least busy
        queue is assigned to the least busy worker.
        """
        resource_manager = tasks.ResourceManager()
        resource_manager._available_queue_task_counts = {
            'worker_1-reserved_1': 7, 'worker_2-reserved_1': 1, 'worker_3-reserved_1': 8,
            'worker_3-reserved_2': 3}

        queue = resource_manager._get_available_queue()

        self.assertEqual(queue, 'worker_2-reserved_1')

    def test__get_available_queue_picks_least_busy_worker(self, active_queues):
        """
        Test that the _get_available_queue() method doesn't pick the least busy queue, when there is
        a busier queue assigned to the least busy worker. It should always pick the least busy
        queue from the least busy worker, not the least busy queue overall.
        """
        resource_manager = tasks.ResourceManager()
        # Worker 2 has the least work here, even though worker_3 has a queue of shorter length.
        resource_manager._available_queue_task_counts = {
            'worker_1-reserved_1': 7, 'worker_2-reserved_1': 3, 'worker_3-reserved_1': 1,
            'worker_3-reserved_2': 3}

        queue = resource_manager._get_available_queue()

        # We should have gotten the queue from worker_2 and not the one from worker_3
        self.assertEqual(queue, 'worker_2-reserved_1')

    def test__get_workers_available_queue_stats_none_assigned(self, active_queues):
        """
        Test the _get_workers_available_queue_stats() method when the requested worker has no queues
        assigned to it. It should raise a NoAvailableQueues Exception.
        """
        resource_manager = tasks.ResourceManager()
        # worker_1 has no assigned reserved queues
        resource_manager._worker_queues = {'worker_1-reserved': []}

        self.assertRaises(tasks.NoAvailableQueues,
                          resource_manager._get_workers_available_queue_stats, 'worker_1-reserved')

    def test__get_workers_available_queue_stats_none_available(self, active_queues):
        """
        Test the _get_workers_available_queue_stats() method when the requested worker has no queues
        available. It should raise a NoAvailableQueues Exception.
        """
        resource_manager = tasks.ResourceManager()
        # Remove 'worker_1-reserved_1 from the _available_queue_task_counts. Since it is the only
        # queue that worker_1-reserved is assigned to, this should cause the NoAvailableQueues
        # Exception to be raised
        del resource_manager._available_queue_task_counts['worker_1-reserved_1']

        self.assertRaises(tasks.NoAvailableQueues,
                          resource_manager._get_workers_available_queue_stats, 'worker_1-reserved')

    def test__get_workers_available_queue_stats_one_available(self, active_queues):
        """
        Test the _get_workers_available_queue_stats() method when the requested worker has one queue
        available. It should return the appropriate data.
        """
        resource_manager = tasks.ResourceManager()
        # Let's set the queue length for worker_1-reserved_1 to a non-zero value so we can assert
        # that the total count is correct later
        resource_manager._available_queue_task_counts['worker_1-reserved_1'] = 7

        stats = resource_manager._get_workers_available_queue_stats('worker_1-reserved')

        self.assertEqual(stats, {'num_tasks': 7, 'least_busy_queue': 'worker_1-reserved_1'})

    def test__get_workers_available_queue_stats_two_available(self, active_queues):
        """
        Test the _get_workers_available_queue_stats() method when the requested worker has two
        queues available. It should return the appropriate data.
        """
        resource_manager = tasks.ResourceManager()
        # Let's set the queue lengths for worker_3-reserved's to non-zero values. We should see the
        # correct num_tasks as well as worker_3-reserved_2 being the least busy
        resource_manager._available_queue_task_counts['worker_3-reserved_1'] = 7
        resource_manager._available_queue_task_counts['worker_3-reserved_2'] = 3

        stats = resource_manager._get_workers_available_queue_stats('worker_3-reserved')

        self.assertEqual(stats, {'num_tasks': 10, 'least_busy_queue': 'worker_3-reserved_2'})


def _reserve_resource_apply_async():
    class AsyncResult(object):
        def get(self):
            return RESERVED_WORKER_1
    return AsyncResult()


class TestTask(PulpServerTests):
    """
    Test the pulp.server.tasks.Task class.
    """
    @mock.patch('pulp.server.async.tasks._queue_release_resource')
    @mock.patch('pulp.server.async.tasks._reserve_resource.apply_async',
                return_value=_reserve_resource_apply_async())
    @mock.patch('pulp.server.async.tasks.Task.apply_async', autospec=True)
    def test_apply_async_with_reservation_calls_apply_async(self, apply_async, _reserve_resource,
                                                            _queue_release_resource):
        """
        Assert that apply_async_with_reservation() calls Celery's apply_async.
        """
        some_args = [1, 'b', 'iii']
        some_kwargs = {'1': 'for the money', '2': 'for the show', 'queue': RESERVED_WORKER_1}
        resource_id = 'three_to_get_ready'
        task = tasks.Task()

        task.apply_async_with_reservation(resource_id, *some_args, **some_kwargs)

        _reserve_resource.assert_called_once_with((resource_id,),
                                                  queue=tasks.RESOURCE_MANAGER_QUEUE)
        apply_async.assert_called_once_with(task, *some_args, **some_kwargs)
        _queue_release_resource.apply_async.assert_called_once_with((resource_id,),
                                                                    queue=RESERVED_WORKER_1)


class TestCancel(PulpServerTests):
    """
    Test the tasks.cancel() function.
    """
    @mock.patch('pulp.server.async.tasks.controller.revoke', autospec=True)
    def test_cancel(self, revoke):
        task_id = '1234abcd'

        tasks.cancel(task_id)

        revoke.assert_called_once_with(task_id, terminate=True)
