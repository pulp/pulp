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


from unittest import TestCase
from mock import Mock, patch

from pulp.plugins.model import Unit
from pulp_citrus.importer.strategies import ImporterStrategy, Mirror


class TestBase(TestCase):

    def test_abstract(self):
        # Setup
        conduit = 1
        config = 2
        downloader = 3
        # Test
        strategy = ImporterStrategy(conduit, config, downloader)
        # Verify
        self.assertEqual(conduit, strategy.conduit)
        self.assertEqual(config, strategy.config)
        self.assertEqual(downloader, strategy.downloader)
        self.assertEqual(conduit, strategy.progress.conduit)
        self.assertRaises(NotImplementedError, strategy.synchronize, None)


class TestConduit:

    def get_units(self):
        return [
            Unit('T', {1:1}, {2:2}, 'path_1'),
            Unit('T', {1:2}, {2:2}, 'path_2'),
            Unit('T', {1:3}, {2:2}, 'path_3'),
        ]

    add_unit = Mock()


class TestMirror(TestCase):

    def setUp(self):
        TestConduit.add_unit.reset_mock()

    def test_successful(self):
        # WORK IN PROGRESS
        pass
