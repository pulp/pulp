# -*- coding: utf-8 -*-
#
# Copyright © 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import unittest

import mock

from pulp.server.exceptions import MissingResource
from pulp.server.managers.factory import initialize
from pulp.server.managers.schedule.consumer import ConsumerScheduleManager


initialize()


class TestValidate(unittest.TestCase):
    def setUp(self):
        super(TestValidate, self).setUp()
        self.manager = ConsumerScheduleManager()

    @mock.patch('pulp.server.managers.consumer.cud.ConsumerManager.get_consumer')
    def test_calls_get_consumer(self, mock_get):
        self.manager._validate_consumer('foo')

        mock_get.assert_called_once_with('foo')

    @mock.patch('pulp.server.db.model.base.Model.get_collection')
    def test_raises_missing(self, mock_get_collection):
        # mock another layer down to verify manager integration
        mock_get_collection.return_value.find_one.side_effect = MissingResource

        self.assertRaises(MissingResource, self.manager._validate_consumer, 'foo')


# TODO: finish testing this class
