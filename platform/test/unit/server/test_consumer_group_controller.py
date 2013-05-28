# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import mock

import base

from pulp.server.itineraries.consumer_group import *
from pulp.server.db.model.consumer import Consumer, ConsumerGroup
from pulp.server.managers import factory as managers
from pulp.server.db.model.criteria import Criteria


GROUP_ID = 'group_1'
CONSUMER_IDS = ('test_1', 'test_2', 'test_3')


class ContentTest(base.PulpWebserviceTests):

    def setUp(self):
        super(self.__class__, self).setUp()
        Consumer.get_collection().remove()
        ConsumerGroup.get_collection().remove()

    def tearDown(self):
        super(self.__class__, self).tearDown()
        Consumer.get_collection().remove()
        ConsumerGroup.get_collection().remove()

    def populate(self):
        manager = managers.consumer_manager()
        for consumer_id in CONSUMER_IDS:
            manager.register(consumer_id)
        manager = managers.consumer_group_manager()
        manager.create_consumer_group(GROUP_ID)
        for consumer_id in CONSUMER_IDS:
            criteria = Criteria(filters={'id': consumer_id}, fields=['id'])
            manager.associate(GROUP_ID, criteria)

    @mock.patch('pulp.server.webservices.controllers.consumer_groups.consumer_group_content_install_itinerary', wraps=consumer_group_content_install_itinerary)
    def test_install(self, mock_itinerary):
        # Setup
        self.populate()
        # Test
        unit_key = dict(name='zsh')
        unit = dict(type_id='rpm', unit_key=unit_key)
        units = [unit,]
        options = dict(importkeys=True)
        path = '/v2/consumer_groups/%s/actions/content/install/' % GROUP_ID
        body = dict(units=units, options=options)
        status, body = self.post(path, body)
        # Verify
        self.assertEquals(status, 202)
        self.assertEqual(len(body), len(CONSUMER_IDS))
        mock_itinerary.assert_called_with(GROUP_ID, units, options)

    @mock.patch('pulp.server.webservices.controllers.consumer_groups.consumer_group_content_update_itinerary', wraps=consumer_group_content_update_itinerary)
    def test_update(self, mock_itinerary):
        # Setup
        self.populate()
        # Test
        unit_key = dict(name='zsh')
        unit = dict(type_id='rpm', unit_key=unit_key)
        units = [unit,]
        options = dict(importkeys=True)
        path = '/v2/consumer_groups/%s/actions/content/update/' % GROUP_ID
        body = dict(units=units, options=options)
        status, body = self.post(path, body)
        # Verify
        self.assertEquals(status, 202)
        self.assertEqual(len(body), len(CONSUMER_IDS))
        mock_itinerary.assert_called_with(GROUP_ID, units, options)

    @mock.patch('pulp.server.webservices.controllers.consumer_groups.consumer_group_content_uninstall_itinerary', wraps=consumer_group_content_uninstall_itinerary)
    def test_uninstall(self, mock_itinerary):
        # Setup
        self.populate()
        # Test
        unit_key = dict(name='zsh')
        unit = dict(type_id='rpm', unit_key=unit_key)
        units = [unit,]
        options = dict(importkeys=True)
        path = '/v2/consumer_groups/%s/actions/content/uninstall/' % GROUP_ID
        body = dict(units=units, options=options)
        status, body = self.post(path, body)
        # Verify
        self.assertEquals(status, 202)
        self.assertEqual(len(body), len(CONSUMER_IDS))
        mock_itinerary.assert_called_with(GROUP_ID, units, options)