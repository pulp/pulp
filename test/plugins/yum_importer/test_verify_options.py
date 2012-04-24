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
import glob
import os
import sys
import mock
import unittest
import tempfile
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../plugins/importers/yum_importer/")
import drpm
import importer_rpm
import importer_mocks
from importer import YumImporter
from pulp.yum_plugin import util
from importer import YUM_IMPORTER_TYPE_ID

class TestVerifyOptions(unittest.TestCase):

    def setUp(self):
        super(TestVerifyOptions, self).setUp()
        self.data_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), "../data"))

    def tearDown(self):
        super(TestVerifyOptions, self).tearDown()

    def test_verify_options(self):
        def side_effect(path):
            # no-op to override file removal
            pass
        util.cleanup_file = mock.Mock()
        util.cleanup_file = side_effect
        test_pkg_path = os.path.join(self.data_dir, "test_repo", "pulp-test-package-0.2.1-1.fc11.x86_64.rpm")
        verify_options = dict(checksum=True, size=True)
        size = 2216
        checksum = "4dbde07b4a8eab57e42ed0c9203083f1d61e0b13935d1a569193ed8efc9ecfd7"
        checksum_type = "sha256"
        exists = util.verify_exists(test_pkg_path, checksum, checksum_type, size, verify_options)
        self.assertTrue(exists)

        # check invalid size
        size = 1232
        t_exists = util.verify_exists(test_pkg_path, checksum, checksum_type, size, verify_options)
        self.assertFalse(t_exists)

        # check None size
        size = None
        exists = util.verify_exists(test_pkg_path, checksum, checksum_type, size, verify_options)
        self.assertTrue(exists)

        # check invalid checksum
        checksum="test_value"
        exists = util.verify_exists(test_pkg_path, checksum, checksum_type, size, verify_options)
        self.assertFalse(exists)

        # skip size/checksum checks
        verify_options = dict(checksum=False, size=False)
        exists = util.verify_exists(test_pkg_path, checksum, checksum_type, size, verify_options)
        self.assertTrue(exists)

        # invalid path
        test_pkg_fake_path = os.path.join(self.data_dir, "test_fake_repo", "pulp-test-package-0.2.1-1.fc11.x86_64.rpm")
        exists = util.verify_exists(test_pkg_fake_path, checksum, checksum_type, size, verify_options)
        self.assertFalse(exists)
