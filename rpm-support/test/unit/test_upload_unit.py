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

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/importers/")
import importer_mocks
from yum_importer.importer import YumImporter
from pulp_rpm.yum_plugin import util

from pulp.plugins.model import Repository
import rpm_support_base

class TestRPMs(rpm_support_base.PulpRPMTests):

    def setUp(self):
        super(TestRPMs, self).setUp()
        self.saved_verify_exists = util.verify_exists
        self.init()

    def tearDown(self):
        super(TestRPMs, self).tearDown()
        util.verify_exists = self.saved_verify_exists
        self.clean()

    def init(self):
        self.temp_dir = tempfile.mkdtemp()
        self.working_dir = os.path.join(self.temp_dir, "working")
        self.pkg_dir = os.path.join(self.temp_dir, "packages")
        self.data_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), "data"))

    def clean(self):
        shutil.rmtree(self.temp_dir)

    def test_upload_rpm(self):
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_upload_rpm"
        upload_conduit = importer_mocks.get_upload_conduit(pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config()
        importer = YumImporter()
        file_path = "%s/%s" % (self.data_dir, "incisura-7.1.4-1.elfake.noarch.rpm")
        metadata = {'filename' : "incisura-7.1.4-1.elfake.noarch.rpm", 'checksum' : 'e0e98e76e4e06dad65a82b0111651d7aca5b00fe'}
        unit_key = {'name' : 'incisura', 'version' : '7.1.4', 'release' : '1', 'arch' : 'noarch', 'checksum' : 'e0e98e76e4e06dad65a82b0111651d7aca5b00fe', 'checksumtype' : 'sha1'}
        print file_path
        type_id = "rpm"
        status, summary, details = importer._upload_unit(repo, type_id, unit_key, metadata, file_path, upload_conduit, config)
        print status, summary, details
        self.assertTrue(status)
        self.assertTrue(summary is not None)
        self.assertTrue(details is not None)
        self.assertEquals(summary["num_units_saved"], 1)
        self.assertEquals(summary["num_units_processed"], 1)
        self.assertEquals(summary["filename"], "incisura-7.1.4-1.elfake.noarch.rpm")
        self.assertEquals(details["errors"], [])

    def test_upload_erratum(self):
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_upload_errata"
        upload_conduit = importer_mocks.get_upload_conduit(pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config()
        importer = YumImporter()
        file_path = []
        type_id = "erratum"
        unit_key = dict()
        unit_key['id'] = "RHBA-2012:0101"
        metadata = {"pkglist" : [],}
        status, summary, details = importer._upload_unit(repo, type_id, unit_key, metadata, file_path, upload_conduit, config)
        self.assertTrue(status)
        self.assertEqual(summary['state'], 'FINISHED')
        print status, summary, details
