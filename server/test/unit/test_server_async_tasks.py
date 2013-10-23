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
    u'worker_1-reserved': [
        {u'exclusive': False, u'name': u'worker_1-reserved_1', u'exchange': {
            u'name': u'worker_1-reserved_1', u'durable': True, u'delivery_mode': 2,
            u'passive': False, u'arguments': None, u'type': u'direct', u'auto_delete': False},
         u'durable': True, u'routing_key': u'worker_1-reserved_1', u'no_ack': False,
         u'alias': None, u'queue_arguments': None, u'binding_arguments': None, u'bindings': [],
         u'auto_delete': False}],
    # This is a worker subscribed to both a reserved resource queue and the general Celery queue,
    # running on worker_2
    u'worker_2-reserved': [
        {u'exclusive': False, u'name': u'worker_2-reserved_1', u'exchange': {
            u'name': u'worker_2-reserved_1', u'durable': True, u'delivery_mode': 2,
            u'passive': False, u'arguments': None, u'type': u'direct', u'auto_delete': False},
         u'durable': True, u'routing_key': u'worker_2-reserved_1', u'no_ack': False,
         u'alias': None, u'queue_arguments': None, u'binding_arguments': None, u'bindings': [],
         u'auto_delete': False},
        {u'exclusive': False, u'name': u'celery', u'exchange': {
            u'name': u'celery', u'durable': True, u'delivery_mode': 2, u'passive': False,
            u'arguments': None, u'type': u'direct', u'auto_delete': False},
         u'durable': True, u'routing_key': u'celery', u'no_ack': False, u'alias': None,
         u'queue_arguments': None, u'binding_arguments': None, u'bindings': [],
         u'auto_delete': False}],
    # This is another worker subscribed to two reserved resource queues
    u'worker_3-reserved': [
        {u'exclusive': False, u'name': u'worker_3-reserved_1', u'exchange': {
            u'name': u'worker_3-reserved_1', u'durable': True, u'delivery_mode': 2,
            u'passive': False, u'arguments': None, u'type': u'direct', u'auto_delete': False},
         u'durable': True, u'routing_key': u'worker_3-reserved_1', u'no_ack': False,
         u'alias': None, u'queue_arguments': None, u'binding_arguments': None, u'bindings': [],
         u'auto_delete': False},
        {u'exclusive': False, u'name': u'worker_3-reserved_2', u'exchange': {
            u'name': u'worker_3-reserved_2', u'durable': True, u'delivery_mode': 2,
            u'passive': False, u'arguments': None, u'type': u'direct', u'auto_delete': False},
         u'durable': True, u'routing_key': u'worker_3-reserved_2', u'no_ack': False,
         u'alias': None, u'queue_arguments': None, u'binding_arguments': None, u'bindings': [],
         u'auto_delete': False}],
    # This is a worker subscribed to the special ReservationManager queue
    u'resource_manager': [
        {u'exclusive': False, u'name': u'resource_manager', u'exchange': {
            u'name': u'resource_manager', u'durable': True, u'delivery_mode': 2, u'passive': False,
            u'arguments': None, u'type': u'direct', u'auto_delete': False},
         u'durable': True, u'routing_key': u'resource_manager', u'no_ack': False, u'alias': None,
         u'queue_arguments': None, u'binding_arguments': None, u'bindings': [],
         u'auto_delete': False}]}


MOCK_RESERVED_QUEUE = 'a_reserved_queue_name'


@mock.patch('celery.app.control.Inspect.active_queues', return_value=MOCK_ACTIVE_QUEUES_RETURN_VALUE)
class TestGetResourceManager(PulpServerTests):
    """
    Test the _get_resource_manager() function.
    """
    @mock.patch('pulp.server.async.tasks._resource_manager', 'a_fake_resource_manager')
    def test_initialized(self, active_queues):
        """
        If the _resource_manager attribute is not None, _get_resource_manager should return it to us
        without instantiating a new ResourceManager.
        """
        resource_manager = tasks._get_resource_manager()

        # Make sure the return value is the expected value
        self.assertEqual(resource_manager, 'a_fake_resource_manager')
        # The module's _resource_manager should remain the same
        self.assertEqual(tasks._resource_manager, 'a_fake_resource_manager')

    @mock.patch('pulp.server.async.tasks._resource_manager', None)
    def test_unitialized(self, active_queues):
        """
        Test the function when it is called for the first time. We've patched the _resource_manager
        module attribute to be None, as it would be before _get_resource_manager() is called for the
        first time.
        """
        # Make sure we are in the expected starting state
        self.assertEqual(tasks._resource_manager, None)

        resource_manager = tasks._get_resource_manager()

        self.assertTrue(isinstance(resource_manager, tasks.ResourceManager))
        # Make sure the singleton instance was saved to the module so it can be returned later.
        self.assertTrue(resource_manager is tasks._resource_manager)


class TestQueueReleaseResource(PulpServerTests):
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


class TestReleaseResource(PulpServerTests):
    """
    Test the _release_resource() Task.
    """
    @mock.patch('pulp.server.async.tasks._resource_manager')
    def test__release_resource(self, _resource_manager):
        """
        Ensure that the _release_resource() Task calls the singleton's release_resource() method
        with the appropriate arguments.
        """
        resource_id = 'a_resource'

        tasks._release_resource.apply_async((resource_id,), queue=tasks.RESOURCE_MANAGER_QUEUE)

        _resource_manager.release_resource.assert_called_once_with(resource_id)


class TestReserveResource(PulpServerTests):
    """
    Test the _reserve_resource() Task.
    """
    @mock.patch('pulp.server.async.tasks._resource_manager')
    def test__reserve_resource(self, _resource_manager):
        """
        Ensure that the _reserve_resource() Task calls the singleton's reserve_resource() method
        with the appropriate arguments.
        """
        a_queue = 'a_special_queue'
        _resource_manager.reserve_resource.return_value = a_queue
        resource_id = 'some_resource'

        async_result = tasks._reserve_resource.apply_async((resource_id,),
                                                           queue=tasks.RESOURCE_MANAGER_QUEUE)

        _resource_manager.reserve_resource.assert_called_once_with(resource_id)
        # Make sure the return value is correct
        self.assertEqual(async_result.get(), a_queue)


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

    def test_release_resource_not_in__resource_map(self, active_queues):
        """
        Test release_resource() with a resource that is not in the _resource_map. This should be
        gracefully handled, and result in no changes to the _resource_map.
        """
        resource_manager = tasks.ResourceManager()
        resource_manager._available_queue_task_counts = {'worker_1-reserved_1': 7,
                                                         'worker_2-reserved_1': 3}
        resource_manager._resource_map = {
            'resource_1': {'queue': 'worker_1-reserved_1', 'task_count': 7},
            'resource_2': {'queue': 'worker_2-reserved_1', 'task_count': 3}}
        expected_available_queue_task_counts = deepcopy(
            resource_manager._available_queue_task_counts)
        expected_resource_map = deepcopy(resource_manager._resource_map)

        # This should not raise any Exception, but should also not alter the resource_map
        resource_manager.release_resource('made_up_resource_id')

        # None of the state variables should have changed
        self.assertEqual(resource_manager._available_queue_task_counts,
                         expected_available_queue_task_counts)
        self.assertEqual(resource_manager._resource_map, expected_resource_map)

    def test_release_resource_queue_task_count_zero(self, active_queues):
        """
        Test release_resource() with a resource that has a queue with a task count of zero. This
        should not decrement the queue task count into the negative range.
        """
        resource_manager = tasks.ResourceManager()
        resource_manager._available_queue_task_counts = {'worker_1-reserved_1': 7,
                                                         'worker_2-reserved_1': 0}
        resource_manager._resource_map = {
            'resource_1': {'queue': 'worker_1-reserved_1', 'task_count': 7},
            'resource_2': {'queue': 'worker_2-reserved_1', 'task_count': 1}}
        expected_available_queue_task_counts = deepcopy(
            resource_manager._available_queue_task_counts)

        # This should remove resource_2 from the _resource_map, but should leave the queue's task
        # count at 0.
        resource_manager.release_resource('resource_2')

        # The _available_queue_task_counts should remain as they were before, since we don't want
        # queue lengths below zero
        self.assertEqual(resource_manager._available_queue_task_counts,
                         expected_available_queue_task_counts)
        # resource_2 should have been removed from the _resource_map
        expected_resource_map = {'resource_1': {'queue': 'worker_1-reserved_1', 'task_count': 7}}
        self.assertEqual(resource_manager._resource_map, expected_resource_map)

    def test_release_resource_task_count_one(self, active_queues):
        """
        Test release_resource() with a resource that has a task count of one. This should remove
        the resource from the _resource_map.
        """
        resource_manager = tasks.ResourceManager()
        resource_manager._available_queue_task_counts = {'worker_1-reserved_1': 7,
                                                         'worker_2-reserved_1': 1}
        resource_manager._resource_map = {
            'resource_1': {'queue': 'worker_1-reserved_1', 'task_count': 7},
            'resource_2': {'queue': 'worker_2-reserved_1', 'task_count': 1}}

        # This should remove resource_2 from the _resource_map, and decrement the queue count for
        # worker_2-reserved_3
        resource_manager.release_resource('resource_2')

        # The task count for worker_2-reserved_3 should have been decremented to 0
        expected_available_queue_task_counts = {'worker_1-reserved_1': 7, 'worker_2-reserved_1': 0}
        self.assertEqual(resource_manager._available_queue_task_counts,
                         expected_available_queue_task_counts)
        # resource_2 should have been removed from the _resource_map
        expected_resource_map = {'resource_1': {'queue': 'worker_1-reserved_1', 'task_count': 7}}
        self.assertEqual(resource_manager._resource_map, expected_resource_map)

    def test_release_resource_task_count_two(self, active_queues):
        """
        Test release_resource() with a resource that has a task count of two. This should simply
        decrement the task_count for the resource, but should not remove it from the _resource_map.
        """
        resource_manager = tasks.ResourceManager()
        resource_manager._available_queue_task_counts = {'worker_1-reserved_1': 7,
                                                         'worker_2-reserved_1': 2}
        resource_manager._resource_map = {
            'resource_1': {'queue': 'worker_1-reserved_1', 'task_count': 7},
            'resource_2': {'queue': 'worker_2-reserved_1', 'task_count': 2}}

        # This should decrement the task count for resource_2 in the _resource_map, and decrement
        # the queue count for worker_2-reserved_3
        resource_manager.release_resource('resource_2')

        # The task count for worker_2-reserved_3 should have been decremented to 1
        expected_available_queue_task_counts = {'worker_1-reserved_1': 7, 'worker_2-reserved_1': 1}
        self.assertEqual(resource_manager._available_queue_task_counts,
                         expected_available_queue_task_counts)
        # resource_2's task count should have been decremented to 1
        expected_resource_map = {'resource_1': {'queue': 'worker_1-reserved_1', 'task_count': 7},
                                 'resource_2': {'queue': 'worker_2-reserved_1', 'task_count': 1}}
        self.assertEqual(resource_manager._resource_map, expected_resource_map)

    def test_reserve_resource_in_resource_map(self, active_queues):
        """
        Test reserve_resource() with a resource that is already in the _resource_map. It should
        return the queue in there, and increment the task counter.
        """
        resource_manager = tasks.ResourceManager()
        resource_manager._available_queue_task_counts = {'worker_1-reserved_1': 7,
                                                         'worker_2-reserved_1': 3}
        resource_manager._resource_map = {
            'resource_1': {'queue': 'worker_1-reserved_1', 'task_count': 7},
            'resource_2': {'queue': 'worker_2-reserved_1', 'task_count': 3}}

        queue = resource_manager.reserve_resource('resource_2')

        self.assertEqual(queue, 'worker_2-reserved_1')
        # The available queue task count for worker_2-reserved_3 should have been incremented
        self.assertEqual(resource_manager._available_queue_task_counts,
                         {'worker_1-reserved_1': 7, 'worker_2-reserved_1': 4})
        # The _resource_map should be the same as before, but now with a task_count of 4 for
        # resource_2
        self.assertEqual(
            resource_manager._resource_map,
            {'resource_1': {'queue': 'worker_1-reserved_1', 'task_count': 7},
             'resource_2': {'queue': 'worker_2-reserved_1', 'task_count': 4}})

    def test_reserve_resource_not_in_resource_map(self, active_queues):
        """
        Test reserve_resource() with a resource that is not in the _resource_map. It should
        return a queue from the least busy worker, and it should add the resource to the
        _resource_map
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
            return MOCK_RESERVED_QUEUE
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
        some_kwargs = {'1': 'for the money', '2': 'for the show', 'queue': MOCK_RESERVED_QUEUE}
        resource_id = 'three_to_get_ready'
        task = tasks.Task()

        task.apply_async_with_reservation(resource_id, *some_args, **some_kwargs)

        _reserve_resource.assert_called_once_with((resource_id,),
                                                  queue=tasks.RESOURCE_MANAGER_QUEUE)
        apply_async.assert_called_once_with(task, *some_args, **some_kwargs)
        _queue_release_resource.apply_async.assert_called_once_with((resource_id,),
                                                                    queue=MOCK_RESERVED_QUEUE)


class TestCancel(PulpServerTests):
    """
    Test the tasks.cancel() function.
    """
    @mock.patch('pulp.server.async.tasks.controller.revoke', autospec=True)
    def test_cancel(self, revoke):
        task_id = '1234abcd'

        tasks.cancel(task_id)

        revoke.assert_called_once_with(task_id, terminate=True)
