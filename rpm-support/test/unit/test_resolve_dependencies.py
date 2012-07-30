#!/usr/bin/python
#
# Copyright (c) 2012 Red Hat, Inc.
#
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
import os
import shutil
import sys
import tempfile
import time
import unittest
import itertools

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/importers/")
import importer_mocks
from yum_importer.importer import YumImporter
from pulp_rpm.yum_plugin import util
from pulp.plugins.model import Repository, Unit
from yum_importer.importer_rpm import RPM_TYPE_ID
import rpm_support_base

class TestResolveDeps(rpm_support_base.PulpRPMTests):

    def setUp(self):
        super(TestResolveDeps, self).setUp()
        self.temp_dir = tempfile.mkdtemp()
        self.working_dir = os.path.join(self.temp_dir, "working")
        self.pkg_dir = os.path.join(self.temp_dir, "packages")
        self.data_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), "data"))

    def tearDown(self):
        super(TestResolveDeps, self).tearDown()
        self.clean()

    def clean(self):
        shutil.rmtree(self.temp_dir)
        # clean up dir created by yum's repostorage
        if os.path.exists("./test_resolve_deps"):
            shutil.rmtree("test_resolve_deps")

    def test_resolve_deps(self):
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.importer_working_dir = "%s/%s" % (self.data_dir, "test_resolve_deps")
        repo.id = "test_resolve_deps"

        unit_key_a = {'id' : '','name' :'pulp-server', 'version' :'0.0.309', 'release' : '1.fc17', 'epoch':'0', 'arch' : 'noarch', 'checksumtype' : 'sha256',
                      'checksum': 'ee5afa0aaf8bd2130b7f4a9b35f4178336c72e95358dd33bda8acaa5f28ea6e9', 'type_id' : 'rpm'}
        unit_key_b = {'id' : '', 'name' :'pulp-rpm-server', 'version' :'0.0.309', 'release' :'1.fc17', 'epoch':'0','arch' : 'noarch', 'checksumtype' :'sha256',
                      'checksum': '1e6c3a3bae26423fe49d26930b986e5f5ee25523c13f875dfcd4bf80f770bf56', 'type_id' : 'rpm'}

        existing_units = []
        for unit in [unit_key_a, unit_key_b]:
            existing_units.append(Unit(RPM_TYPE_ID, unit, {}, ''))
        dependency_conduit = importer_mocks.get_dependency_conduit(type_id=RPM_TYPE_ID, existing_units=existing_units, pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config()
        importer = YumImporter()
        units = [Unit(RPM_TYPE_ID, unit_key_b, {}, '')]
        report = importer.resolve_dependencies(repo, units, dependency_conduit, config)
        self.assertTrue(report.success_flag)
        self.assertTrue(report.summary is not None)
        self.assertTrue(report.details is not None)
        self.assertEqual(len(list(itertools.chain(*report.summary['resolved'].values()))), 1)
