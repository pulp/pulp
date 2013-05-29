#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
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
import logging
import mock_plugins
import mock_agent

from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.consumer import ConsumerGroup
from pulp.server.managers import factory as manager_factory

class ConsumerGroupAssociationTests(base.PulpWebserviceTests):
    def setUp(self):
        super(ConsumerGroupAssociationTests, self).setUp()
        self.manager = manager_factory.consumer_group_manager()

    def clean(self):
        super(ConsumerGroupAssociationTests, self).clean()
        ConsumerGroup.get_collection().remove()

    @mock.patch.object(Criteria, 'from_client_input', return_value=Criteria())
    @mock.patch('pulp.server.managers.consumer.group.cud.ConsumerGroupManager.associate')
    def test_associate(self, mock_associate, mock_from_client):
        self.manager.create_consumer_group('cg1')

        post_data = {'criteria': {'filters':{'id':{'$in':['consumer1']}}}}
        status, body = self.post('/v2/consumer_groups/cg1/actions/associate/', post_data)
        self.assertEqual(status, 200)

        self.assertEqual(mock_associate.call_count, 1)
        call_args = mock_associate.call_args[0]
        self.assertEqual(call_args[0], 'cg1')
        # verify that it created and used a Criteria instance
        self.assertEqual(call_args[1], mock_from_client.return_value)
        self.assertEqual(mock_from_client.call_args[0][0],
                {'filters':{'id':{'$in':['consumer1']}}})

    @mock.patch.object(Criteria, 'from_client_input', return_value=Criteria())
    @mock.patch('pulp.server.managers.consumer.group.cud.ConsumerGroupManager.unassociate')
    def test_unassociate(self, mock_unassociate, mock_from_client):
        self.manager.create_consumer_group('cg1')

        post_data = {'criteria': {'filters':{'id':{'$in':['consumer1']}}}}
        status, body = self.post('/v2/consumer_groups/cg1/actions/unassociate/', post_data)
        self.assertEqual(status, 200)

        self.assertEqual(mock_unassociate.call_count, 1)
        call_args = mock_unassociate.call_args[0]
        self.assertEqual(call_args[0], 'cg1')
        # verify that it created and used a Criteria instance
        self.assertEqual(call_args[1], mock_from_client.return_value)
        self.assertEqual(mock_from_client.call_args[0][0],
                {'filters':{'id':{'$in':['consumer1']}}})
        
