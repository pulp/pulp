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
This module contains tests for the pulp.server.async.tasks module.
"""
from datetime import datetime, timedelta
import signal
import unittest
import uuid

from celery.app import defaults
from celery.result import AsyncResult
import celery
import mock

from ...base import PulpServerTests, ResourceReservationTests
from pulp.common import dateutils
from pulp.devel.unit.util import compare_dict
from pulp.server.exceptions import PulpException, PulpCodedException
from pulp.server.async import tasks
from pulp.server.async.task_status_manager import TaskStatusManager
from pulp.server.db.model.dispatch import TaskStatus
from pulp.server.db.model.resources import AvailableQueue, ReservedResource
from pulp.server.async.constants import (CALL_CANCELED_STATE, CALL_FINISHED_STATE,
                                            CALL_RUNNING_STATE, CALL_WAITING_STATE)


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
    @mock.patch('pulp.server.async.tasks.subprocess_active_queues', return_value=None)
    def test_active_queues_none(self, subprocess_active_queues):
        """
        When there are no active queues, the active_queues.py subprocess will print null.
        subprocess_active_queues will in turn return None. We had a traceback upon the first
        worker's startup due to this, so this test makes sure that babysit() handles this scenario
        gracefully.
        """
        # This should not cause any Exception
        tasks.babysit()

    @mock.patch('pulp.server.async.tasks.subprocess_active_queues',
                return_value=MOCK_ACTIVE_QUEUES_RETURN_VALUE)
    @mock.patch('pulp.server.async.tasks.cancel')
    @mock.patch('pulp.server.async.tasks.controller.add_consumer')
    @mock.patch('pulp.server.async.tasks.logger')
    def test_babysit_cancels_correct_tasks(self, logger, add_consumer, cancel,
                                           subprocess_active_queues):
        """
        When babysit() discovers that a worker has gone missing, it should cancel all of the tasks
        that were in its queue.
        """
        # Let's start off by creating the existing queues and what not by calling babysit
        tasks.babysit()
        # Now, let's add another AvailableQueue that isn't found in our active_queues mock so that
        # babysit() can notice that it appears to have gone missing next time it's called. We need
        # to also mark it as having been missing for at least 5 minutes.
        missing_available_queue = AvailableQueue('%s4' % tasks.RESERVED_WORKER_NAME_PREFIX, 2,
                                                 datetime.utcnow() - timedelta(minutes=5))
        missing_available_queue.save()
        # Let's simulate three tasks being assigned to this AvailableQueue, with two of them being
        # in an incomplete state and one in a complete state. The two should get canceled.
        # Let's put task_1 in progress
        task_1 = TaskStatusManager.create_task_status('task_1', missing_available_queue.name,
                                                      state=CALL_RUNNING_STATE)
        task_2 = TaskStatusManager.create_task_status('task_2', missing_available_queue.name,
                                                      state=CALL_WAITING_STATE)
        # This task shouldn't get canceled because it isn't in an incomplete state
        task_3 = TaskStatusManager.create_task_status('task_3', missing_available_queue.name,
                                                      state=CALL_FINISHED_STATE)
        # Let's make a task in a worker that is still present just to make sure it isn't touched.
        task_4 = TaskStatusManager.create_task_status('task_4', RESERVED_WORKER_1,
                                                      state=CALL_RUNNING_STATE)

        # Now, let's call babysit() again. This time, it should delete the AvailableQueue, and it
        # should cancel task_1 and task_2. task_3 should be left alone.
        tasks.babysit()

        # cancel() should have been called twice with task_1 and task_2 as parameters
        self.assertEqual(cancel.call_count, 2)
        # Let's build a set out of the two times that cancel was called. We can't know for sure
        # which order the Tasks got canceled in, but we can assert that the correct two tasks were
        # canceled (task_3 should not appear in this set).
        cancel_param_set = set([c[1] for c in cancel.mock_calls])
        self.assertEqual(cancel_param_set, set([('task_1',), ('task_2',)]))
        # We should have logged that we are canceling the tasks
        self.assertEqual(logger.call_count, 0)
        self.assertTrue(missing_available_queue.name in logger.mock_calls[0][1][0])
        self.assertTrue('Canceling the tasks' in logger.mock_calls[0][1][0])

    @mock.patch('pulp.server.async.tasks.subprocess_active_queues',
                return_value=MOCK_ACTIVE_QUEUES_RETURN_VALUE)
    @mock.patch('pulp.server.async.tasks.controller.add_consumer')
    def test_babysit_creates_correct_records(self, add_consumer, subprocess_active_queues):
        """
        Test babysit() with a blank database. It should create the correct AvailableQueues.
        """
        tasks.babysit()

        # babysit() should have called the subprocess_active_queues() method
        subprocess_active_queues.assert_called_once_with()
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

    @mock.patch('pulp.server.async.tasks.subprocess_active_queues',
                return_value=MOCK_ACTIVE_QUEUES_RETURN_VALUE)
    @mock.patch('pulp.server.async.tasks._delete_queue.apply_async',
                side_effect=tasks._delete_queue.apply_async)
    @mock.patch('pulp.server.async.tasks.controller.add_consumer')
    def test_babysit_deletes_correct_records(self, add_consumer, _delete_queue_apply_async,
                                             subprocess_active_queues):
        """
        Test babysit() with pre-existing state. It should create the correct AvailableQueues, and
        delete other ones, and leave others in place.
        """
        # This AvailableQueue should remain in the DB
        available_queue_2 = AvailableQueue(name=RESERVED_WORKER_2)
        available_queue_2.save()
        # This AvailableQueue doesn't exist anymore since it's not in the mock results, and it's
        # been missing for five minutes, so it should get deleted
        available_queue_4 = AvailableQueue(name='%s4' % tasks.RESERVED_WORKER_NAME_PREFIX,
                                           missing_since=datetime.utcnow() - timedelta(minutes=5))
        available_queue_4.save()
        # This AvailableQueue doesn't exist anymore since it's not in the mock results, but it's
        # been missing for less than five minutes, so it should not get deleted
        available_queue_5 = AvailableQueue(name='%s5' % tasks.RESERVED_WORKER_NAME_PREFIX,
                                           missing_since=datetime.utcnow() - timedelta(minutes=2))
        available_queue_5.save()
        # This AvailableQueue doesn't exist anymore since it's not in the mock results, but it
        # hasn't been missing before (i.e., it's missing_since attribute is None), so it should not
        # get deleted. It's missing_since attribute should be set to a datetime, however.
        available_queue_6 = AvailableQueue(name='%s6' % tasks.RESERVED_WORKER_NAME_PREFIX,
                                           missing_since=None)
        available_queue_6.save()

        # This should cause queue 4 to get deleted, and 6 to get marked as missing.
        tasks.babysit()

        # babysit() should have called the subprocess_active_queues() method
        subprocess_active_queues.assert_called_once_with()
        # There should be five ActiveQueues, one for each reserved worker in the mock data (3), and
        # numbers 5 and 6 that we created above should also remain because they have been missing
        # for less than five minutes.
        aqc = AvailableQueue.get_collection()
        self.assertEqual(aqc.count(), 5)
        # Let's make sure their names, num_reservations counts, and missing_since attributes are
        # correct
        aq_1 = aqc.find_one({'_id': RESERVED_WORKER_1})
        self.assertEqual(aq_1['num_reservations'], 0)
        self.assertEqual(aq_1['missing_since'], None)
        aq_2 = aqc.find_one({'_id': RESERVED_WORKER_2})
        self.assertEqual(aq_2['num_reservations'], 0)
        self.assertEqual(aq_2['missing_since'], None)
        aq_3 = aqc.find_one({'_id': RESERVED_WORKER_3})
        self.assertEqual(aq_3['num_reservations'], 0)
        self.assertEqual(aq_3['missing_since'], None)

        # Numbers 5 and 6 should exist, with non-null missing_since attributes
        aq_5 = aqc.find_one({'_id': '%s5' % tasks.RESERVED_WORKER_NAME_PREFIX})
        self.assertEqual(aq_5['num_reservations'], 0)
        self.assertEqual(type(aq_5['missing_since']), datetime)
        self.assertTrue(aq_5['missing_since'] < datetime.utcnow() - timedelta(minutes=2))
        aq_6 = aqc.find_one({'_id': '%s6' % tasks.RESERVED_WORKER_NAME_PREFIX})
        self.assertEqual(aq_6['num_reservations'], 0)
        self.assertEqual(type(aq_6['missing_since']), datetime)
        self.assertTrue(aq_6['missing_since'] < datetime.utcnow())

        # Reserved worker 3 wasn't assigned to a queue, so babysit() should have assigned it to one
        add_consumer.assert_called_once_with(queue=RESERVED_WORKER_3,
                                             destination=(RESERVED_WORKER_3,))

        # Make sure that _delete_queue was called for #4, and that the delete task was sent to the
        # RESOURCE_MANAGER_QUEUE
        _delete_queue_apply_async.assert_called_once_with(
            args=('%s4' % tasks.RESERVED_WORKER_NAME_PREFIX,), queue=tasks.RESOURCE_MANAGER_QUEUE)

    @mock.patch('pulp.server.async.tasks.subprocess_active_queues',
                return_value=MOCK_ACTIVE_QUEUES_RETURN_VALUE)
    @mock.patch('pulp.server.async.tasks.controller.add_consumer')
    def test_babysit_resets_missing_since_on_reappearing_workers(self, add_consumer,
                                                                 subprocess_active_queues):
        """
        Let's simulate an AvailableQueue having been missing in the past by setting its
        missing_since attribute to two minutes ago. It is part of the mocked active_queues() call,
        so we expect babysit() to set its missing_since attribute back to None. Note that this one
        has been missing for more than five minutes, but it got lucky because it is back just in
        time to avoid being deleted.
        """
        available_queue_2 = AvailableQueue(name=RESERVED_WORKER_2,
                                           missing_since=datetime.utcnow() - timedelta(minutes=6))
        available_queue_2.save()

        tasks.babysit()

        # babysit() should have called the subprocess_active_queues() method
        subprocess_active_queues.assert_called_once_with()
        # There should be three ActiveQueues, one for each reserved worker in the mock data
        aqc = AvailableQueue.get_collection()
        self.assertEqual(aqc.count(), 3)
        # Make sure it's set back to None
        aq_2 = aqc.find_one({'_id': RESERVED_WORKER_2})
        self.assertEqual(aq_2['num_reservations'], 0)
        self.assertEqual(aq_2['missing_since'], None)


class TestDeleteQueue(ResourceReservationTests):
    """
    Test the _delete_queue() Task.
    """
    @mock.patch('pulp.server.async.tasks.controller.add_consumer')
    @mock.patch('pulp.server.async.tasks.subprocess_active_queues',
                return_value=MOCK_ACTIVE_QUEUES_RETURN_VALUE)
    @mock.patch('pulp.server.async.tasks.cancel')
    @mock.patch('pulp.server.async.tasks.logger')
    def test__delete_queue(self, logger, cancel, subprocess_active_queues, mock_add_consumer):
        """
        Assert that the correct Tasks get canceled when their queue is deleted, and that the queue
        is removed from the database.
        """
        # Let's start off by creating the existing queues and what not by calling babysit
        tasks.babysit()
        # Let's simulate three tasks being assigned to RESERVED_WORKER_2, with two of them being
        # in an incomplete state and one in a complete state. We will delete RESERVED_WORKER_2's
        # queue, which should cause the two to get canceled. Let's put task_1 in progress
        task_1 = TaskStatusManager.create_task_status('task_1', RESERVED_WORKER_2,
                                                      state=CALL_RUNNING_STATE)
        task_2 = TaskStatusManager.create_task_status('task_2', RESERVED_WORKER_2,
                                                      state=CALL_WAITING_STATE)
        # This task shouldn't get canceled because it isn't in an incomplete state
        task_3 = TaskStatusManager.create_task_status('task_3', RESERVED_WORKER_2,
                                                      state=CALL_FINISHED_STATE)
        # Let's make a task in a worker that is still present just to make sure it isn't touched.
        task_4 = TaskStatusManager.create_task_status('task_4', RESERVED_WORKER_1,
                                                      state=CALL_RUNNING_STATE)
        # Let's just make sure the babysit() worked and that we have an AvailableQueue with RR2
        aqc = AvailableQueue.get_collection()
        self.assertEqual(aqc.find({'_id': RESERVED_WORKER_2}).count(), 1)

        # Now let's delete the queue named RESERVED_WORKER_2
        tasks._delete_queue.apply_async(args=(RESERVED_WORKER_2,),
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
        self.assertTrue(RESERVED_WORKER_2 in logger.mock_calls[0][1][0])
        self.assertTrue('Canceling the tasks' in logger.mock_calls[0][1][0])

        # The queue should have been deleted
        self.assertEqual(aqc.find({'_id': RESERVED_WORKER_2}).count(), 0)
        # The other queues (1 and 3) should remain
        self.assertEqual(aqc.find().count(), 2)


class TestInitializeWorker(unittest.TestCase):
    """
    Test the initialize_worker() function.
    """
    @mock.patch('pulp.server.async.tasks.babysit')
    def test_initialize_worker(self, babysit):
        """
        Test that initialize_worker() makes the correct calls.
        """
        tasks._initialize_worker()

        # babysit() should have been called with no args
        babysit.assert_called_once_with()


class TestSubprocessActiveQueues(unittest.TestCase):
    """
    Test the subprocess_active_queues() function.
    """

    @mock.patch('pulp.server.async.tasks.json')
    @mock.patch('pulp.server.async.tasks.Popen')
    @mock.patch('pulp.server.async.tasks.PIPE')
    def test_subprocess_active_queues(self, PIPE, Popen, json):
        """
        Test that subprocess_active_queues() makes the correct calls.
        """
        command = ['python', '-m', 'pulp.server.async.active_queues']
        json_argument = mock.Mock()
        communicate_result = [json_argument]
        popen_result = mock.Mock()
        popen_result.communicate.return_value = communicate_result
        Popen.return_value = popen_result
        active_queues = mock.Mock()
        json.loads.return_value = active_queues
        result = tasks.subprocess_active_queues()
        Popen.assert_called_with(command, stdout=PIPE)
        json.loads.assert_called_with(json_argument)
        self.assertTrue(result is active_queues)


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
        some_kwargs = {'1': 'for the money', '2': 'for the show', 'queue': RESERVED_WORKER_1}
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
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'queue': RESERVED_WORKER_2}
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
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'queue': RESERVED_WORKER_2}
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
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'queue': RESERVED_WORKER_2}
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
        kwargs = {'1': 'for the money', 'tags': ['test_tags'], 'queue': RESERVED_WORKER_1}
        apply_async.return_value = celery.result.AsyncResult('test_task_id')
        task = tasks.Task()

        task.apply_async(*args, **kwargs)

        task_statuses = list(TaskStatusManager.find_all())
        self.assertEqual(len(task_statuses), 1)
        new_task_status = task_statuses[0]
        self.assertEqual(new_task_status['task_id'], 'test_task_id')
        self.assertEqual(new_task_status['queue'], RESERVED_WORKER_1)
        self.assertEqual(new_task_status['tags'], kwargs['tags'])
        self.assertEqual(new_task_status['state'], 'waiting')

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
    def test_apply_async_task_canceled(self, apply_async):
        """
        Assert that apply_async() honors 'canceled' task status.
        """
        args = [1, 'b', 'iii']
        kwargs = {'1': 'for the money', 'tags': ['test_tags']}
        task_id = 'test_task_id'
        TaskStatusManager.create_task_status(task_id, AvailableQueue('test-queue'), state=CALL_CANCELED_STATE)
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
        test_queue = AvailableQueue('test_queue')
        TaskStatusManager.create_task_status(task_id, test_queue.name)
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
        task_id = '1234abcd'
        test_queue = AvailableQueue('test_queue')
        TaskStatusManager.create_task_status(task_id, test_queue.name, state=CALL_FINISHED_STATE)
        self.assertRaises(PulpCodedException, tasks.cancel, task_id)

        task_status = TaskStatusManager.find_by_task_id(task_id)
        self.assertEqual(task_status['state'], CALL_FINISHED_STATE)

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
