"""
This module contains tests for the pulp.server.managers.resources module.
"""
from datetime import datetime
import types

import mock
import pymongo

from ...base import ResourceReservationTests
from pulp.server.exceptions import NoWorkers
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.resources import Worker, ReservedResource
from pulp.server.managers import resources


class TestFilterWorkers(ResourceReservationTests):

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


class TestGetWorkerForReservation(ResourceReservationTests):

    def setUp(self):
        self.patch_a = mock.patch('pulp.server.managers.resources.resources', autospec=True)
        self.mock_resources = self.patch_a.start()

        self.patch_b = mock.patch('pulp.server.managers.resources.criteria', autospec=True)
        self.mock_criteria = self.patch_b.start()

        super(TestGetWorkerForReservation, self).setUp()

    def tearDown(self):
        self.patch_a.stop()
        self.patch_b.stop()
        super(TestGetWorkerForReservation, self).tearDown()

    def test_existing_reservation_correctly_found(self):
        resources.get_worker_for_reservation('resource1')
        get_collection = self.mock_resources.ReservedResource.get_collection
        get_collection.assert_called_once_with()
        get_collection.return_value.find_one.assert_called_once_with({'resource_id': 'resource1'})

    def test_criteria_by_name_for_a_found_reservation_built_correctly(self):
        find_one = self.mock_resources.ReservedResource.get_collection.return_value.find_one
        find_one.return_value = {'worker_name': 'worker1'}
        resources.get_worker_for_reservation('resource1')
        self.mock_criteria.Criteria.assert_called_once_with({'_id': 'worker1'})

    def test_correct_worker_bson_found(self):
        find_one = self.mock_resources.ReservedResource.get_collection.return_value.find_one
        find_one.return_value = {'worker_name': 'worker1'}
        resources.get_worker_for_reservation('resource1')
        get_collection = self.mock_resources.Worker.get_collection
        get_collection.assert_called_once_with()
        query = get_collection.return_value.query
        query.assert_called_once_with(self.mock_criteria.Criteria.return_value)

    def test_correct_worker_returned(self):
        find_one = self.mock_resources.ReservedResource.get_collection.return_value.find_one
        find_one.return_value = {'worker_name': 'worker1'}
        result = resources.get_worker_for_reservation('resource1')
        self.assertTrue(result is self.mock_resources.Worker.from_bson.return_value)

    def test_no_workers_raised_if_no_reservations(self):
        find_one = self.mock_resources.ReservedResource.get_collection.return_value.find_one
        find_one.return_value = False
        try:
            resources.get_worker_for_reservation('resource1')
        except NoWorkers:
            pass
        else:
            self.fail("NoWorkers() Exception should have been raised.")


class TestGetUnreservedWorker(ResourceReservationTests):

    def setUp(self):
        self.patch_a = mock.patch('pulp.server.managers.resources.filter_workers')
        self.mock_filter_workers = self.patch_a.start()

        self.patch_b = mock.patch('pulp.server.managers.resources.criteria')
        self.mock_criteria = self.patch_b.start()

        self.patch_c = mock.patch('pulp.server.managers.resources.resources', autospec=True)
        self.mock_resources = self.patch_c.start()

        super(TestGetUnreservedWorker, self).setUp()

    def tearDown(self):
        self.patch_a.stop()
        self.patch_b.stop()
        self.patch_c.stop()
        super(TestGetUnreservedWorker, self).tearDown()

    def test_workers_correctly_queried(self):
        self.mock_filter_workers.return_value = [{'name': 'a'}, {'name': 'b'}]
        resources.get_unreserved_worker()
        self.mock_criteria.Criteria.assert_called_once_with()
        self.mock_filter_workers.assert_called_once_with(self.mock_criteria.Criteria.return_value)

    def test_reserved_resources_queried_correctly(self):
        find = self.mock_resources.ReservedResource.get_collection.return_value.find
        find.return_value = [{'worker_name': 'a'}, {'worker_name': 'b'}]
        try:
            resources.get_unreserved_worker()
        except NoWorkers:
            pass
        else:
            self.fail("NoWorkers() Exception should have been raised.")
        self.mock_resources.ReservedResource.get_collection.assert_called_once_with()
        find.assert_called_once_with()

    def test_worker_returned_when_one_worker_is_not_reserved(self):
        self.mock_filter_workers.return_value = [{'name': 'a'}, {'name': 'b'}]
        find = self.mock_resources.ReservedResource.get_collection.return_value.find
        find.return_value = [{'worker_name': 'a'}]
        result = resources.get_unreserved_worker()
        self.assertEqual(result, {'name': 'b'})

    def test_no_workers_raised_when_all_workers_reserved(self):
        self.mock_filter_workers.return_value = [{'name': 'a'}, {'name': 'b'}]
        find = self.mock_resources.ReservedResource.get_collection.return_value.find
        find.return_value = [{'worker_name': 'a'}, {'worker_name': 'b'}]
        try:
            resources.get_unreserved_worker()
        except NoWorkers:
            pass
        else:
            self.fail("NoWorkers() Exception should have been raised.")

    def test_no_workers_raised_when_there_are_no_workers(self):
        self.mock_filter_workers.return_value = []
        find = self.mock_resources.ReservedResource.get_collection.return_value.find
        find.return_value = [{'worker_name': 'a'}, {'worker_name': 'b'}]
        try:
            resources.get_unreserved_worker()
        except NoWorkers:
            pass
        else:
            self.fail("NoWorkers() Exception should have been raised.")
