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
This module contains tests for the pulp.server.managers.resources module.
"""
from ...base import ResourceReservationTests
from pulp.server.db.model.resources import AvailableQueue
from pulp.server.managers import resources


class TestGetLeastBusyAvailableQueue(ResourceReservationTests):
    """
    Test the get_least_busy_available_queue_function().
    """
    def test_no_queues_available(self):
        """
        Test for the case when there are no reserved queues available at all.
        It should raise a NoAvailableQueues Exception.
        """
        # When no queues are available, a NoAvailableQueues Exception should be raised
        self.assertRaises(resources.NoAvailableQueues, resources.get_least_busy_available_queue)

    def test_picks_least_busy_queue(self):
        """
        Test that the function picks the least busy queue.
        """
        # Set up three available queues, with the least busy one in the middle so that we can
        # demonstrate that it did pick the least busy and not the last or first.
        available_queue_1 = AvailableQueue('busy_queue', 7)
        available_queue_1.save()
        available_queue_2 = AvailableQueue('less_busy_queue', 3)
        available_queue_2.save()
        available_queue_3 = AvailableQueue('most_busy_queue', 10)
        available_queue_3.save()

        queue = resources.get_least_busy_available_queue()

        self.assertEqual(type(queue), AvailableQueue)
        self.assertEqual(queue.num_reservations, 3)
        self.assertEqual(queue.name, 'less_busy_queue')
