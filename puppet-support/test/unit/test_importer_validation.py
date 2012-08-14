# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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
import unittest

from pulp_puppet.common import constants
from pulp_puppet.importer import config


class FeedTests(unittest.TestCase):

    def test_validate_feed(self):
        # Test
        result, msg = config._validate_feed({constants.CONFIG_FEED : 'http://localhost'})

        # Verify
        self.assertTrue(result)
        self.assertTrue(msg is None)

    def test_validate_feed_missing(self):
        # Test
        result, msg = config._validate_feed({})

        # Verify
        self.assertTrue(result)
        self.assertTrue(msg is None)

    def test_validate_feed_invalid(self):
        # Test
        result, msg = config._validate_feed({constants.CONFIG_FEED : 'bad-feed'})

        # Verify
        self.assertTrue(not result)
        self.assertTrue(msg is not None)
        self.assertTrue('bad-feed' in msg)


class QueriesTests(unittest.TestCase):

    def test_validate_queries(self):
        # Test
        result, msg = config._validate_queries({constants.CONFIG_QUERIES : ['httpd', 'mysql']})

        # Verify
        self.assertTrue(result)
        self.assertTrue(msg is None)

    def test_validate_queries_missing(self):
        # Test
        result, msg = config._validate_queries({})

        # Verify
        self.assertTrue(result)
        self.assertTrue(msg is None)

    def test_validate_queries_invalid(self):
        # Test
        result, msg = config._validate_queries({constants.CONFIG_QUERIES : 'non-list'})

        # Verify
        self.assertTrue(not result)
        self.assertTrue(msg is not None)
        self.assertTrue(constants.CONFIG_QUERIES in msg)


class RemoveMissingTests(unittest.TestCase):

    def test_validate_remove_missing(self):
        # Test
        result, msg = config._validate_remove_missing({constants.CONFIG_REMOVE_MISSING : 'true'})

        # Verify
        self.assertTrue(result)
        self.assertTrue(msg is None)

    def test_validate_remove_missing_missing(self):
        # Test
        result, msg = config._validate_remove_missing({})

        # Verify
        self.assertTrue(result)
        self.assertTrue(msg is None)

    def test_validate_remove_missing_invalid(self):
        # Test
        result, msg = config._validate_remove_missing({constants.CONFIG_REMOVE_MISSING : 'foo'})

        # Verify
        self.assertTrue(not result)
        self.assertTrue(msg is not None)
        self.assertTrue(constants.CONFIG_REMOVE_MISSING in msg)


class FullValidationTests(unittest.TestCase):

    @mock.patch('pulp_puppet.importer.config._validate_feed')
    @mock.patch('pulp_puppet.importer.config._validate_queries')
    @mock.patch('pulp_puppet.importer.config._validate_remove_missing')
    def test_validate(self, missing, queries, feed):
        """
        Tests that the validate() call aggregates to all of the specific test
        calls.
        """
        all_mock_calls = locals()
        all_mock_calls.pop('self')
        all_mock_calls = all_mock_calls.values()

        # Setup
        for x in all_mock_calls:
            x.return_value = True, None

        # Test
        c = {}
        config.validate(c)

        # Verify
        for x in all_mock_calls:
            x.assert_called_once_with(c)