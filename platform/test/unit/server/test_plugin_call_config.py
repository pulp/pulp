# -*- coding: utf-8 -*-
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

import unittest

from pulp.plugins.config import PluginCallConfiguration


class PluginCallConfigurationTests(unittest.TestCase):

    def setUp(self):
        super(PluginCallConfigurationTests, self).setUp()

        self.override_config = {'a' : 'a4', 'b' : 'b4', 'e' : 'e4'}
        self.repo_plugin_config = {'a' : 'a3', 'c' : 'c3'}
        self.plugin_config = {'a' : 'a2', 'b' : 'b2', 'd' : 'd2'}
        self.default_config = {'a' : 'a1'}

        self.config = PluginCallConfiguration(self.plugin_config,
                                              self.repo_plugin_config,
                                              self.override_config)
        self.config.default_config = self.default_config

    def test_flatten(self):
        # Test
        flattened = self.config.flatten()

        # Verify
        self.assertTrue(isinstance(flattened, dict))
        self.assertEqual(5, len(flattened))
        self.assertEqual(flattened['a'], 'a4')
        self.assertEqual(flattened['b'], 'b4')
        self.assertEqual(flattened['c'], 'c3')
        self.assertEqual(flattened['d'], 'd2')
        self.assertEqual(flattened['e'], 'e4')
