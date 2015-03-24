"""
This module contains tests for the pulp.server.db.model.resources module.
"""
import mock
import uuid

from ....base import ResourceReservationTests
from pulp.server.db.model import resources


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
