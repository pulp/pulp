"""
This module contains tests for the pulp.server.db.model.resources module.
"""
from datetime import datetime
import mock

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

    def test_delete_with_reserved_resources(self):
        """
        Test delete() for a Worker with a ReservedResource referencing its queue_name.
        """
        now = datetime.utcnow()
        worker = resources.Worker('worker_with_a_reserved_resource', now)
        worker.save()
        workers_collection = resources.Worker.get_collection()
        self.assertEqual(workers_collection.find({'_id': worker.name}).count(), 1)

        # Create 3 resources, 2 referencing the worker to be deleted and 1 with no worker references
        rr1 = resources.ReservedResource('reserved_resource1', assigned_queue=worker.queue_name,
                                         num_reservations=1)
        rr2 = resources.ReservedResource('reserved_resource2', assigned_queue=worker.queue_name,
                                         num_reservations=1)
        rr = resources.ReservedResource('reserved_resource_no_queue', num_reservations=0)
        for r in (rr1, rr2, rr):
            r.save()
        rrc = resources.ReservedResource.get_collection()
        self.assertEqual(rrc.count(), 3)
        self.assertEqual(rrc.find({'assigned_queue': worker.queue_name}).count(), 2)

        worker.delete()

        # Make sure that only the resource with reference to the deleted Worker's queue_name is
        # deleted
        self.assertEqual(workers_collection.count(), 0)
        self.assertEqual(rrc.count(), 1)
        self.assertFalse(rrc.find_one(
            {'_id': 'reserved_resource_no_queue', 'num_reservations': 0}) is None)

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
    """
    Test the ReservedResource class.
    """
    @mock.patch('pulp.server.db.model.resources.Model.__init__',
                side_effect=resources.Model.__init__, autospec=True)
    def test___init__(self, super_init):
        """
        Test the __init__() method.
        """
        rr = resources.ReservedResource('some_resource', 'some_queue', 7)

        # The superclass __init__ should have been called
        super_init.assert_called_once_with(rr)
        # Make sure the attributes are correct
        self.assertEqual(rr.name, 'some_resource')
        self.assertEqual(rr.assigned_queue, 'some_queue')
        self.assertEqual(rr.num_reservations, 7)
        self.assertEqual('_id' in rr, False)
        self.assertEqual('id' in rr, False)

    @mock.patch('pulp.server.db.model.resources.Model.__init__',
                side_effect=resources.Model.__init__, autospec=True)
    def test___init___defaults(self, super_init):
        """
        Test __init__() with default values.
        """
        rr = resources.ReservedResource('some_resource')

        # The superclass __init__ should have been called
        super_init.assert_called_once_with(rr)
        # Make sure the attributes are correct
        self.assertEqual(rr.name, 'some_resource')
        # assigned_queue defaults to None
        self.assertEqual(rr.assigned_queue, None)
        # num_reservations should default to False
        self.assertEqual(rr.num_reservations, 1)
        self.assertEqual('_id' in rr, False)
        self.assertEqual('id' in rr, False)

    def test_decrement_num_reservations_doesnt_exist(self):
        """
        decrement_num_reservations() should raise a DoesNotExist when asked to decrement an
        ReservedResource that does not exist in the database.
        """
        rr = resources.ReservedResource('does-not-exist')

        self.assertRaises(base.DoesNotExist, rr.decrement_num_reservations)

    def test_decrement_num_reservations_from_one(self):
        """
        Test decrement_num_reservations() when num_reservations is 1. It should decrement to 0, and
        it should get deleted from the database.
        """
        rr = resources.ReservedResource('a_resource', 'some_queue', 1)
        rr.save()

        rr.decrement_num_reservations()

        # The instance should have been updated
        self.assertEqual(rr.num_reservations, 0)
        self.assertEqual(rr.assigned_queue, 'some_queue')
        # The database should have also been deleted
        rrc = resources.ReservedResource.get_collection()
        self.assertEqual(rrc.count(), 0)

    def test_decrement_num_reservations_from_zero(self):
        """
        Test decrement_num_reservations() when num_reservations is 0. It should remain at 0, and get
        deleted.
        """
        rr = resources.ReservedResource('a_resource', 'some_queue', 0)
        rr.save()

        rr.decrement_num_reservations()

        # The instance should not have been changed
        self.assertEqual(rr.num_reservations, 0)
        self.assertEqual(rr.assigned_queue, 'some_queue')
        # The database should also not have been changed
        rrc = resources.ReservedResource.get_collection()
        self.assertEqual(rrc.count(), 0)

    def test_delete(self):
        """
        Test delete().
        """
        rr = resources.ReservedResource('wont_exist_for_long', num_reservations=0)
        rr.save()
        rrc = resources.ReservedResource.get_collection()
        self.assertEqual(rrc.find({'_id': 'wont_exist_for_long'}).count(), 1)

        rr.delete()

        self.assertEqual(rrc.count(), 0)

    def test_delete_still_reserved(self):
        """
        Test delete() with a ReservedResource that is still reserved. Nothing should happen.
        """
        rr = resources.ReservedResource('wont_exist_for_long', num_reservations=1)
        rr.save()

        rr.delete()

        # The record should not have been deleted.
        rrc = resources.ReservedResource.get_collection()
        self.assertEqual(rrc.count(), 1)
        self.assertEqual(rrc.find({'_id': 'wont_exist_for_long'}).count(), 1)

    def test_increment_num_reservations(self):
        """
        Test increment_num_reservations().
        """
        rr = resources.ReservedResource('some_resource', 'some_queue', 7)
        rr.save()

        rr.increment_num_reservations()

        # The instance and the DB record should both have num_reservations of 8 now
        self.assertEqual(rr.num_reservations, 8)
        self.assertEqual(rr.assigned_queue, 'some_queue')
        rrc = resources.ReservedResource.get_collection()
        self.assertEqual(rrc.find_one({'_id': 'some_resource'})['num_reservations'], 8)

    def test_increment_num_reservations_doesnt_exist(self):
        """
        increment_num_reservations() should raise a DoesNotExist when asked to increment an
        ReservedResource that does not exist in the database.
        """
        rr = resources.ReservedResource('does-not-exist')

        self.assertRaises(base.DoesNotExist, rr.increment_num_reservations)

    def test_save(self):
        """
        Test the save() method.
        """
        rr = resources.ReservedResource('a_resource', 'a_queue', 13)

        rr.save()

        # Make sure the DB has the correct data
        rrc = resources.ReservedResource.get_collection()
        self.assertEqual(rrc.count(), 1)
        self.assertEqual(rrc.find_one({'_id': 'a_resource'})['num_reservations'], 13)
        self.assertEqual(rrc.find_one({'_id': 'a_resource'})['assigned_queue'], 'a_queue')
