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
from pulp_puppet.distributor import configuration


class HttpTests(unittest.TestCase):

    def test_validate_serve_http(self):
        # Test
        config = PluginCallConfiguration({constants.CONFIG_SERVE_HTTP : 'true'}, {})
        result, msg = configuration._validate_http(config)

        # Verify
        self.assertTrue(result)
        self.assertTrue(msg is None)

    def test_validate_serve_http_invalid(self):
        # Test
        config = PluginCallConfiguration({constants.CONFIG_SERVE_HTTP : 'foo'}, {})
        result, msg = configuration._validate_http(config)

        # Verify
        self.assertTrue(not result)
        self.assertTrue(msg is not None)
        self.assertTrue(constants.CONFIG_SERVE_HTTP in msg)


class HttpsTests(unittest.TestCase):

    def test_validate_serve_https(self):
        # Test
        config = PluginCallConfiguration({constants.CONFIG_SERVE_HTTPS : 'true'}, {})
        result, msg = configuration._validate_https(config)

        # Verify
        self.assertTrue(result)
        self.assertTrue(msg is None)

    def test_validate_serve_https_invalid(self):
        # Test
        config = PluginCallConfiguration({constants.CONFIG_SERVE_HTTPS : 'foo'}, {})
        result, msg = configuration._validate_https(config)

        # Verify
        self.assertTrue(not result)
        self.assertTrue(msg is not None)
        self.assertTrue(constants.CONFIG_SERVE_HTTPS in msg)


class FullValidationTests(unittest.TestCase):

    @mock.patch('pulp_puppet.distributor.configuration._validate_http')
    @mock.patch('pulp_puppet.distributor.configuration._validate_https')
    def test_validate(self, mock_https, mock_http):
        # Setup
        all_mock_calls = (mock_http, mock_https)

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

    @mock.patch('pulp_puppet.distributor.configuration._validate_http')
    @mock.patch('pulp_puppet.distributor.configuration._validate_https')
    def test_validate_with_failure(self, mock_https, mock_http):
        # Setup
        all_mock_calls = (mock_http, mock_https)

        for x in all_mock_calls:
            x.return_value = True, None
        all_mock_calls[0].return_value = False, 'foo'

        # Test
        c = PluginCallConfiguration({}, {})
        result, msg = configuration.validate(c)

        # Verify
        self.assertTrue(not result)
        self.assertTrue(msg is not None)
        self.assertEqual(msg, 'foo')

        all_mock_calls[0].assert_called_once_with(c)
        for x in all_mock_calls[1:]:
            self.assertEqual(0, x.call_count)

