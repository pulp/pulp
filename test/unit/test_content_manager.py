# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os
import shutil
import sys
import tempfile
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../common')))

import testutil

from pulp.server.content import manager


class ManagerInstanceTest(testutil.PulpTest):

    def test_manager_instantiation(self):
        try:
            m = manager.Manager()
        except Exception, e:
            self.fail('\n'.join((repr(e), traceback.format_exc())))


class ManagerPathTest(testutil.PulpTest):

    def setUp(self):
        super(ManagerPathTest, self).setUp()
        self.manager = manager.Manager()

    def tearDown(self):
        super(ManagerPathTest, self).tearDown()
        self.manager = None

    def test_add_valid_path(self):
        path = tempfile.mkdtemp()
        self.manager.add_importer_plugin_path(path)
        self.assertTrue(path in self.manager.importer_plugin_paths)
        self.manager.add_importer_config_path(path)
        self.assertTrue(path in self.manager.importer_config_paths)
        self.manager.add_distributor_plugin_path(path)
        self.assertTrue(path in self.manager.distributor_plugin_paths)
        self.manager.add_distributor_config_path(path)
        self.assertTrue(path in self.manager.distributor_config_paths)
        os.rmdir(path)

    def test_add_invalid_path(self):
        non_existent = '/asdf/jkl'
        cant_read = '/root'
        self.assertRaises(ValueError, self.manager.add_importer_plugin_path, non_existent)
        self.assertRaises(ValueError, self.manager.add_distributor_plugin_path, cant_read)


class ManagerLoadTest(ManagerPathTest):
    pass
