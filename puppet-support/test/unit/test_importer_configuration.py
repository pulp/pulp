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

from pulp.plugins.config import PluginCallConfiguration

from pulp_puppet.common import constants
from pulp_puppet.importer import configuration


class FeedTests(unittest.TestCase):

    def test_validate_feed(self):
        # Test
        config = PluginCallConfiguration({constants.CONFIG_FEED : 'http://localhost'}, {})
        result, msg = configuration._validate_feed(config)

        # Verify
        self.assertTrue(result)
        self.assertTrue(msg is None)

    def test_validate_feed_missing(self):
        # Test
        config = PluginCallConfiguration({}, {})
        result, msg = configuration._validate_feed(config)

        # Verify
        self.assertTrue(result)
        self.assertTrue(msg is None)

    def test_validate_feed_invalid(self):
        # Test
        config = PluginCallConfiguration({constants.CONFIG_FEED : 'bad-feed'}, {})
        result, msg = configuration._validate_feed(config)

        # Verify
        self.assertTrue(not result)
        self.assertTrue(msg is not None)
        self.assertTrue('bad-feed' in msg)


class QueriesTests(unittest.TestCase):

    def test_validate_queries(self):
        # Test
        config = PluginCallConfiguration({constants.CONFIG_QUERIES : ['httpd', 'mysql']}, {})
        result, msg = configuration._validate_queries(config)

        # Verify
        self.assertTrue(result)
        self.assertTrue(msg is None)

    def test_validate_queries_missing(self):
        # Test
        config = PluginCallConfiguration({}, {})
        result, msg = configuration._validate_queries(config)

        # Verify
        self.assertTrue(result)
        self.assertTrue(msg is None)

    def test_validate_queries_invalid(self):
        # Test
        config = PluginCallConfiguration({constants.CONFIG_QUERIES : 'non-list'}, {})
        result, msg = configuration._validate_queries(config)

        # Verify
        self.assertTrue(not result)
        self.assertTrue(msg is not None)
        self.assertTrue(constants.CONFIG_QUERIES in msg)


class RemoveMissingTests(unittest.TestCase):

    def test_validate_remove_missing(self):
        # Test
        config = PluginCallConfiguration({constants.CONFIG_REMOVE_MISSING : 'true'}, {})
        result, msg = configuration._validate_remove_missing(config)

        # Verify
        self.assertTrue(result)
        self.assertTrue(msg is None)

    def test_validate_remove_missing_missing(self):
        # Test
        config = PluginCallConfiguration({}, {})
        result, msg = configuration._validate_remove_missing(config)

        # Verify
        self.assertTrue(result)
        self.assertTrue(msg is None)

    def test_validate_remove_missing_invalid(self):
        # Test
        config = PluginCallConfiguration({constants.CONFIG_REMOVE_MISSING : 'foo'}, {})
        result, msg = configuration._validate_remove_missing(config)

        # Verify
        self.assertTrue(not result)
        self.assertTrue(msg is not None)
        self.assertTrue(constants.CONFIG_REMOVE_MISSING in msg)


class FullValidationTests(unittest.TestCase):

    @mock.patch('pulp_puppet.importer.configuration._validate_feed')
    @mock.patch('pulp_puppet.importer.configuration._validate_queries')
    @mock.patch('pulp_puppet.importer.configuration._validate_remove_missing')
    def test_validate(self, missing, queries, feed):
        """
        Tests that the validate() call aggregates to all of the specific test
        calls.
        """
        # Setup
        all_mock_calls = (feed, missing, queries)

        for x in all_mock_calls:
            x.return_value = True, None

        # Test
        c = PluginCallConfiguration({}, {})
        result, msg = configuration.validate(c)

        # Verify
        self.assertTrue(result)
        self.assertTrue(msg is None)

        for x in all_mock_calls:
            x.assert_called_once_with(c)

    @mock.patch('pulp_puppet.importer.configuration._validate_feed')
    @mock.patch('pulp_puppet.importer.configuration._validate_queries')
    @mock.patch('pulp_puppet.importer.configuration._validate_remove_missing')
    def test_validate_with_failure(self, missing, queries, feed):
        """
        Tests that the validate() call aggregates to all of the specific test
        calls.
        """
        # Setup
        all_mock_calls = (feed, missing, queries)

        for x in all_mock_calls:
            x.return_value = True, None
        all_mock_calls[1].return_value = False, 'foo'

        # Test
        c = {}
        result, msg = configuration.validate(c)

        # Verify
        self.assertTrue(not result)
        self.assertEqual(msg, 'foo')

        all_mock_calls[0].assert_called_once_with(c)
        all_mock_calls[1].assert_called_once_with(c)
        self.assertEqual(0, all_mock_calls[2].call_count)
