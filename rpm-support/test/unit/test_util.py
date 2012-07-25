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

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/importers/")

import rpm_support_base
from pulp_rpm.yum_plugin import util


class TestUtil(rpm_support_base.PulpRPMTests):

    def setUp(self):
        super(TestUtil, self).setUp()
        self.init()

    def tearDown(self):
        super(TestUtil, self).tearDown()
        self.clean()

    def init(self):
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), "data"))

    def clean(self):
        shutil.rmtree(self.temp_dir)

    def test_is_rpm_newer(self):
        rpm_a = {"name": "rpm_test_name", "epoch":"0", "release":"el6.1", "version":"2", "arch":"noarch"}
        newer_a = {"name": "rpm_test_name", "epoch":"0", "release":"el6.1", "version":"3", "arch":"noarch"}
        newer_a_diff_arch = {"name": "rpm_test_name", "epoch":"0", "release":"el6.1", "version":"2", "arch":"i386"}
        rpm_b = {"name": "rpm_test_name_B", "epoch":"0", "release":"el6.1", "version":"5", "arch":"noarch"}

        self.assertTrue(util.is_rpm_newer(newer_a, rpm_a))
        self.assertFalse(util.is_rpm_newer(newer_a_diff_arch, rpm_a))
        self.assertFalse(util.is_rpm_newer(rpm_a, newer_a))
        self.assertFalse(util.is_rpm_newer(newer_a, rpm_b))


