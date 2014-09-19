"""
This module contains tests for the pulp.server.db.model.resources module.
"""
from datetime import datetime
import mock
import uuid

from ....base import ResourceReservationTests
from pulp.server.db.model import base, resources


class TestWorker(ResourceReservationTests):
    """
    Test the Worker class.
    """
    @mock.patch('pulp.server.db.model.resources.Model.__init__',
                side_effect=resources.Model.__init__, autospec=True)
    def test___init__(self, super_init):
        """
        Test the __init__() method.
        """
        now = datetime.utcnow()

        worker = resources.Worker('some_name', now)

        # The superclass __init__ should have been called
        super_init.assert_called_once_with(worker)
        # Make sure the attributes are correct
        self.assertEqual(worker.name, 'some_name')
        self.assertEqual(worker.last_heartbeat, now)
        self.assertEqual('_id' in worker, False)
        self.assertEqual('id' in worker, False)

    @mock.patch('pulp.server.db.model.resources.Model.__init__',
                side_effect=resources.Model.__init__, autospec=True)
    def test___init___defaults(self, super_init):
        """
        Test __init__() with default values.
        """
        now = datetime.utcnow()
        worker = resources.Worker('some_name', now)

        # The superclass __init__ should have been called
        super_init.assert_called_once_with(worker)
        # Make sure the attributes are correct
        self.assertEqual(worker.name, 'some_name')
        self.assertEqual(worker.last_heartbeat, now)
        self.assertEqual('_id' in worker, False)
        self.assertEqual('id' in worker, False)

    def test_delete(self):
        """
        Test delete().
        """
        now = datetime.utcnow()
        worker = resources.Worker('wont_exist_for_long', now)
        worker.save()
        workers_collection = resources.Worker.get_collection()
        self.assertEqual(workers_collection.find({'_id': 'wont_exist_for_long'}).count(), 1)

        worker.delete()

        self.assertEqual(workers_collection.count(), 0)

    def test_from_bson(self):
        """
        Test from_bson().
        """
        last_heartbeat = datetime(2013, 12, 16)
        worker = resources.Worker('a_worker', last_heartbeat)
        worker.save()
        workers_collection = resources.Worker.get_collection()
        worker_bson = workers_collection.find_one({'_id': 'a_worker'})

        # Replace the worker reference with a newly instantiated Worker from our bson
        worker = resources.Worker.from_bson(worker_bson)

        self.assertEqual(worker.name, 'a_worker')
        self.assertEqual(worker.last_heartbeat, last_heartbeat)

    def test_save(self):
        """
        Test the save() method.
        """
        last_heartbeat = datetime(2013, 12, 16)

        worker = resources.Worker('a_worker', last_heartbeat)

        worker.save()

        # Make sure the DB has the correct data
        workers_collection = resources.Worker.get_collection()
        self.assertEqual(workers_collection.count(), 1)
        saved_worker = workers_collection.find_one({'_id': 'a_worker'})
        self.assertEqual(saved_worker['last_heartbeat'], last_heartbeat)


class TestReservedResource(ResourceReservationTests):

    def test_unique_indices(self):
        self.assertEqual(resources.ReservedResource.unique_indices, tuple())

    def test_search_indices(self):
        self.assertEqual(resources.ReservedResource.search_indices, ('worker_name', 'resource_id'))

    @mock.patch('pulp.server.db.model.resources.Model.__init__',
                side_effect=resources.Model.__init__, autospec=True)
    def test___init__(self, super_init):
        task_id = uuid.uuid4()
        rr = resources.ReservedResource(task_id, 'some_worker', 'some_resource')

        # The superclass __init__ should have been called
        super_init.assert_called_once_with(rr)
        # Make sure the attributes are correct
        self.assertEqual(rr.task_id, task_id)
        self.assertEqual(rr.worker_name, 'some_worker')
        self.assertEqual(rr.resource_id, 'some_resource')
        self.assertEqual('_id' in rr, False)
        self.assertEqual('id' in rr, False)

    def test_delete(self):
        task_id = uuid.uuid4()
        rr = resources.ReservedResource(task_id, 'some_worker', 'some_resource')
        rr.save()
        rrc = resources.ReservedResource.get_collection()
        self.assertEqual(rrc.find({'_id': task_id}).count(), 1)

        rr.delete()

        self.assertEqual(rrc.count(), 0)

    def test_save(self):
        task_id = uuid.uuid4()
        rr = resources.ReservedResource(task_id, 'some_worker', 'some_resource')

        rr.save()

        # Make sure the DB has the correct data
        rrc = resources.ReservedResource.get_collection()
        self.assertEqual(rrc.count(), 1)
        self.assertEqual(rrc.find_one({'_id': task_id})['worker_name'], 'some_worker')
        self.assertEqual(rrc.find_one({'_id': task_id})['resource_id'], 'some_resource')
