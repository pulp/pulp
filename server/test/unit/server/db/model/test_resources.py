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
This module contains tests for the pulp.server.db.model.resources module.
"""
import mock

from ....base import ResourceReservationTests
from pulp.server.db.model import base, resources


class TestAvailableQueue(ResourceReservationTests):
    """
    Test the AvailableQueue class.
    """
    @mock.patch('pulp.server.db.model.resources.Model.__init__',
                side_effect=resources.Model.__init__, autospec=True)
    def test___init__(self, super_init):
        """
        Test the __init__() method.
        """
        aq = resources.AvailableQueue('some_name', 7)

        # The superclass __init__ should have been called
        super_init.assert_called_once_with(aq)
        # Make sure the attributes are correct
        self.assertEqual(aq.name, 'some_name')
        self.assertEqual(aq.num_reservations, 7)
        self.assertEqual('_id' in aq, False)
        self.assertEqual('id' in aq, False)

    @mock.patch('pulp.server.db.model.resources.Model.__init__',
                side_effect=resources.Model.__init__, autospec=True)
    def test___init___defaults(self, super_init):
        """
        Test __init__() with default values.
        """
        aq = resources.AvailableQueue('some_name')

        # The superclass __init__ should have been called
        super_init.assert_called_once_with(aq)
        # Make sure the attributes are correct
        self.assertEqual(aq.name, 'some_name')
        # num_reservations should default to False
        self.assertEqual(aq.num_reservations, 0)
        self.assertEqual('_id' in aq, False)
        self.assertEqual('id' in aq, False)

    def test_decrement_num_reservations_doesnt_exist(self):
        """
        decrement_num_reservations() should raise a DoesNotExist when asked to decrement an
        AvailableQueue that does not exist in the database.
        """
        aq = resources.AvailableQueue('does-not-exist')

        self.assertRaises(base.DoesNotExist, aq.decrement_num_reservations)

    def test_decrement_num_reservations_from_one(self):
        """
        Test decrement_num_reservations() when num_reservations is 1. It should decrement to 0.
        """
        aq = resources.AvailableQueue('a_queue', 1)
        aq.save()

        aq.decrement_num_reservations()

        # The instance should have been updated
        self.assertEqual(aq.num_reservations, 0)
        # The database should have also been updated
        aqc = resources.AvailableQueue.get_collection()
        self.assertEqual(aqc.count(), 1)
        self.assertEqual(aqc.find_one({'_id': 'a_queue'})['num_reservations'], 0)

    def test_decrement_num_reservations_from_zero(self):
        """
        Test decrement_num_reservations() when num_reservations is 0. It should remain at 0.
        """
        aq = resources.AvailableQueue('a_queue', 0)
        aq.save()

        aq.decrement_num_reservations()

        # The instance should not have been changed
        self.assertEqual(aq.num_reservations, 0)
        # The database should also not have been changed
        aqc = resources.AvailableQueue.get_collection()
        self.assertEqual(aqc.count(), 1)
        self.assertEqual(aqc.find_one({'_id': 'a_queue'})['num_reservations'], 0)

    def test_delete(self):
        """
        Test delete().
        """
        aq = resources.AvailableQueue('wont_exist_for_long')
        aq.save()
        aqc = resources.AvailableQueue.get_collection()
        self.assertEqual(aqc.find({'_id': 'wont_exist_for_long'}).count(), 1)

        aq.delete()

        self.assertEqual(aqc.count(), 0)

    def test_increment_num_reservations(self):
        """
        Test increment_num_reservations().
        """
        aq = resources.AvailableQueue('some_queue', 7)
        aq.save()

        aq.increment_num_reservations()

        # The instance and the DB record should both have num_reservations of 8 now
        self.assertEqual(aq.num_reservations, 8)
        aqc = resources.AvailableQueue.get_collection()
        self.assertEqual(aqc.find_one({'_id': 'some_queue'})['num_reservations'], 8)

    def test_increment_num_reservations_doesnt_exist(self):
        """
        increment_num_reservations() should raise a DoesNotExist when asked to increment an
        AvailableQueue that does not exist in the database.
        """
        aq = resources.AvailableQueue('does-not-exist')

        self.assertRaises(base.DoesNotExist, aq.increment_num_reservations)

    def test_save(self):
        """
        Test the save() method.
        """
        aq = resources.AvailableQueue('a_queue', 13)

        aq.save()

        # Make sure the DB has the correct data
        aqc = resources.AvailableQueue.get_collection()
        self.assertEqual(aqc.count(), 1)
        self.assertEqual(aqc.find_one({'_id': 'a_queue'})['num_reservations'], 13)


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
