# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import unittest

import mock

from pulp.client.commands.consumer import bind as consumer_bind


class InstantiationTests(unittest.TestCase):

    def setUp(self):
        self.mock_context = mock.MagicMock()

    def tearDown(self):
        self.mock_context = None

    def test_bind(self):
        try:
            consumer_bind.ConsumerBindCommand(self.mock_context)
        except Exception, e:
            self.fail(str(e))

    def test_unbind(self):
        try:
            consumer_bind.ConsumerUnbindCommand(self.mock_context)
        except Exception, e:
            self.fail(str(e))

