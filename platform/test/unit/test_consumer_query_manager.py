#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import base

from pulp.server.db.model.consumer import Consumer
import pulp.server.managers.consumer.cud as consumer_manager
import pulp.server.managers.consumer.query as query_manager

# -- test cases ---------------------------------------------------------------

class ConsumerQueryManagerTests(base.PulpServerTests):

    def clean(self):
        base.PulpServerTests.clean(self)
        Consumer.get_collection().remove()
        
    def setUp(self):
        base.PulpServerTests.setUp(self)

        self.consumer_manager = consumer_manager.ConsumerManager()
        self.query_manager = query_manager.ConsumerQueryManager()

    def tearDown(self):
        base.PulpServerTests.tearDown(self)

    def test_find_all(self):
        """
        Tests finding all consumers.
        """

        # Setup
        self.consumer_manager.register('consumer-1')
        self.consumer_manager.register('consumer-2')

        # Test
        results = self.query_manager.find_all()

        # Verify
        self.assertTrue(results is not None)
        self.assertEqual(2, len(results))

        ids = [c['id'] for c in results]
        self.assertTrue('consumer-1' in ids)
        self.assertTrue('consumer-2' in ids)

    def test_find_all_no_results(self):
        """
        Tests that finding all consumers when none are present does not error and
        correctly returns an empty list.
        """

        # Test
        results = self.query_manager.find_all()

        # Verify
        self.assertTrue(results is not None)
        self.assertEqual(0, len(results))

    def test_find_by_id(self):
        """
        Tests finding an existing consumer by its ID.
        """

        # Setup
        self.consumer_manager.register('consumer-1')
        self.consumer_manager.register('consumer-2')

        # Test
        consumer = self.query_manager.find_by_id('consumer-2')

        # Verify
        self.assertTrue(consumer is not None)
        self.assertEqual('consumer-2', consumer['id'])

    def test_find_by_id_no_consumer(self):
        """
        Tests attempting to find a consumer that doesn't exist by its ID does not
        raise an error and correctly returns none.
        """

        # Setup
        self.consumer_manager.register('consumer-1')

        # Test
        consumer = self.query_manager.find_by_id('not-there')

        # Verify
        self.assertTrue(consumer is None)

    def test_find_by_id_list(self):
        """
        Tests finding a list of consumers by ID.
        """

        # Setup
        self.consumer_manager.register('consumer-1')
        self.consumer_manager.register('consumer-2')
        self.consumer_manager.register('consumer-3')

        # Test
        consumers = self.query_manager.find_by_id_list(['consumer-2', 'consumer-1'])

        # Verify
        self.assertEqual(2, len(consumers))

        ids = [c['id'] for c in consumers]
        self.assertTrue('consumer-2' in ids)
        self.assertTrue('consumer-1' in ids)
