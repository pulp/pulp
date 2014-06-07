"""
This module contains tests for the pulp.server.managers.resources module.
"""
from datetime import datetime
import types

import mock
import pymongo

from ...base import ResourceReservationTests
from pulp.server import exceptions
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.resources import Worker, ReservedResource
from pulp.server.managers import resources


class TestFilterWorkers(ResourceReservationTests):
    """
    Test the filter_workers() function.
    """
    @mock.patch('pulp.server.db.model.resources.Worker.get_collection')
    def test_criteria_passed_to_mongo(self, get_collection):
        """
        Assert that the Criteria object is passed on to MongoDB.
        """
        criteria = Criteria(filters={'_id': 'some_id'})

        workers = list(resources.filter_workers(criteria))

        get_collection.return_value.query.assert_called_once_with(criteria)
        self.assertEqual(workers, list())

    def test_filter(self):
        """
        Test a filter operation to make sure the results appear to be correct.
        """
        # Make three workers. We'll filter for two of them.
        now = datetime.utcnow()
        kw_1 = Worker('worker_1', now)
        kw_1.save()
        kw_2 = Worker('worker_2', now)
        kw_2.save()
        kw_3 = Worker('worker_3', now)
        kw_3.save()
        criteria = Criteria(filters={'_id': {'$gt': 'worker_1'}}, sort=[('_id', pymongo.ASCENDING)])

        workers = resources.filter_workers(criteria)

        # Let's assert that workers is a generator, and then let's cast it to a list so it's easier
        # to test that we got the correct instances back.
        self.assertEqual(type(workers), types.GeneratorType)
        workers = list(workers)
        self.assertEqual(all([isinstance(w, Worker) for w in workers]), True)
        self.assertEqual(workers[0].name, 'worker_2')
        self.assertEqual(workers[1].name, 'worker_3')


class TestGetLeastBusyWorker(ResourceReservationTests):
    """
    Test the get_least_busy_available_worker() function.
    """
    def test_ignores_queues_that_arent_workers(self):
        """
        It is possible for the assigned_queue in a ReservedResource to reference a queue that is not
        in the workers collection. This test ensures that this queue is properly ignored, even if it
        is the most "enticing" choice.
        """
        # Set up three Workers, with the least busy one in the middle so that we can
        # demonstrate that it did pick the least busy and not the last or first.
        now = datetime.utcnow()
        worker_1 = Worker('busy_worker', now)
        worker_2 = Worker('less_busy_worker', now)
        worker_3 = Worker('most_busy_worker', now)
        for worker in (worker_1, worker_2, worker_3):
            worker.save()
        # Now we need to make some reservations against these Workers' queues. We'll give worker_1
        # 8 reservations, putting it in the middle of busyness.
        rr_1 = ReservedResource(name='resource_1', assigned_queue=worker_1.queue_name,
                                num_reservations=8)
        # These next two will give worker_2 a total of 7 reservations, so it should get picked.
        rr_2 = ReservedResource(name='resource_2', assigned_queue=worker_2.queue_name,
                                num_reservations=3)
        rr_3 = ReservedResource(name='resource_3', assigned_queue=worker_2.queue_name,
                                num_reservations=4)
        # These next three will give worker_3 a total of 9 reservations, so it should be the most
        # busy.
        rr_4 = ReservedResource(name='resource_4', assigned_queue=worker_3.queue_name,
                                num_reservations=2)
        rr_5 = ReservedResource(name='resource_5', assigned_queue=worker_3.queue_name,
                                num_reservations=3)
        rr_6 = ReservedResource(name='resource_6', assigned_queue=worker_3.queue_name,
                                num_reservations=4)
        # Now we will make a ReservedResource that references a queue that does not correspond to a
        # Worker and has the lowest reservation count. This RR should be ignored.
        rr_7 = ReservedResource(name='resource_7', assigned_queue='doesnt_exist',
                                num_reservations=1)
        for rr in (rr_1, rr_2, rr_3, rr_4, rr_5, rr_6, rr_7):
            rr.save()

        worker = resources.get_least_busy_worker()

        self.assertEqual(type(worker), Worker)
        self.assertEqual(worker.name, 'less_busy_worker')

    def test_no_workers_available(self):
        """
        Test for the case when there are no Workers at all.
        It should raise a NoWorkers Exception.
        """
        # When no workers are available, a NoWorkers Exception should be raised
        self.assertRaises(exceptions.NoWorkers, resources.get_least_busy_worker)

    def test_picks_least_busy_worker(self):
        """
        Test that the function picks the least busy worker.
        """
        # Set up three Workers, with the least busy one in the middle so that we can
        # demonstrate that it did pick the least busy and not the last or first.
        now = datetime.utcnow()
        worker_1 = Worker('busy_worker', now)
        worker_2 = Worker('less_busy_worker', now)
        worker_3 = Worker('most_busy_worker', now)
        for worker in (worker_1, worker_2, worker_3):
            worker.save()
        # Now we need to make some reservations against these Workers' queues. We'll give worker_1
        # 8 reservations, putting it in the middle of busyness.
        rr_1 = ReservedResource(name='resource_1', assigned_queue=worker_1.queue_name,
                                num_reservations=8)
        # These next two will give worker_2 a total of 7 reservations, so it should get picked.
        rr_2 = ReservedResource(name='resource_2', assigned_queue=worker_2.queue_name,
                                num_reservations=3)
        rr_3 = ReservedResource(name='resource_3', assigned_queue=worker_2.queue_name,
                                num_reservations=4)
        # These next three will give worker_3 a total of 9 reservations, so it should be the most
        # busy.
        rr_4 = ReservedResource(name='resource_4', assigned_queue=worker_3.queue_name,
                                num_reservations=2)
        rr_5 = ReservedResource(name='resource_5', assigned_queue=worker_3.queue_name,
                                num_reservations=3)
        rr_6 = ReservedResource(name='resource_6', assigned_queue=worker_3.queue_name,
                                num_reservations=4)
        for rr in (rr_1, rr_2, rr_3, rr_4, rr_5, rr_6):
            rr.save()

        worker = resources.get_least_busy_worker()

        self.assertEqual(type(worker), Worker)
        self.assertEqual(worker.name, 'less_busy_worker')


class TestGetOrCreateReservedResource(ResourceReservationTests):
    """
    Test the get_or_create_reserved_resource() function.
    """
    def test_create(self):
        """
        Test for the case when the requested resource does not exist.
        """
        # Let's add an ReservedResource just to make sure that it doesn't return any existing
        # resource.
        rr_1 = ReservedResource('resource_1')
        rr_1.save()

        rr_2 = resources.get_or_create_reserved_resource('resource_2')

        # Assert that the returned instance is correct
        self.assertEqual(type(rr_2), ReservedResource)
        self.assertEqual(rr_2.name, 'resource_2')
        # By default, the assigned_queue should be set to None
        self.assertEqual(rr_2.assigned_queue, None)
        # A new resource should default to 1 reservations
        self.assertEqual(rr_2.num_reservations, 1)
        # Now we need to assert that it made it to the database as well
        rrc = rr_2.get_collection()
        self.assertEqual(rrc.find_one({'_id': 'resource_2'})['num_reservations'], 1)
        self.assertEqual(rrc.find_one({'_id': 'resource_2'})['assigned_queue'], None)

    def test_get(self):
        """
        Test for the case when the requested resource does exist.
        """
        # Let's add two ReservedResources just to make sure that it doesn't return the wrong
        # resource.
        rr_1 = ReservedResource('resource_1')
        rr_1.save()
        rr_2 = ReservedResource('resource_2', 'some_queue', 7)
        rr_2.save()

        rr_2 = resources.get_or_create_reserved_resource('resource_2')

        # Assert that the returned instance is correct
        self.assertEqual(type(rr_2), ReservedResource)
        self.assertEqual(rr_2.name, 'resource_2')
        self.assertEqual(rr_2.assigned_queue, 'some_queue')
        # The resource should have 7 reservations
        self.assertEqual(rr_2.num_reservations, 7)
        # Now we need to assert that the DB is still correct
        rrc = rr_2.get_collection()
        self.assertEqual(rrc.find_one({'_id': 'resource_2'})['num_reservations'], 7)
        self.assertEqual(rrc.find_one({'_id': 'resource_2'})['assigned_queue'], 'some_queue')
