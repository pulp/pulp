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

import glob
import mock
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest

from grinder.BaseFetch import BaseFetch

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/importers/")

import rpm_support_base
import importer_mocks

from yum_importer.importer import YumImporter, YUM_IMPORTER_TYPE_ID
from yum_importer import importer_rpm
from yum_importer.importer_rpm import RPM_TYPE_ID, RPM_UNIT_KEY

from pulp.plugins.model import Repository, Unit
from pulp_rpm.yum_plugin import util


class TestCleanup(rpm_support_base.PulpRPMTests):

    def setUp(self):
        super(TestCleanup, self).setUp()
        self.saved_verify_exists = util.verify_exists
        self.init()

    def tearDown(self):
        super(TestCleanup, self).tearDown()
        util.verify_exists = self.saved_verify_exists
        self.clean()

    def init(self):
        self.temp_dir = tempfile.mkdtemp()
        self.working_dir = os.path.join(self.temp_dir, "working")
        self.pkg_dir = os.path.join(self.temp_dir, "packages")
        self.data_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), "data"))

    def clean(self):
        shutil.rmtree(self.temp_dir)

    def test_simple_yum_ops_a(self):
        feed_url = "file://empty"
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_simple_yum_ops"
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        grind = importer_rpm.get_yumRepoGrinder(repo.id, repo.working_dir, config)
        try:
            grind.setup(basepath=repo.working_dir, num_retries=0, retry_delay=0)
        except:
            pass
        self.assertFalse(os.path.exists(os.path.join("./", repo.id)))

    def test_yum_only_ops(self):
        import sys
        import yum
        import traceback
        repo_id = "test_yum_only_ops"
        feed_url = "file://empty"
        expected_dir = os.path.join("./", repo_id)
        if os.path.exists(expected_dir):
            shutil.rmtree(expected_dir)
        self.assertFalse(os.path.exists(expected_dir))
        yum_repo = yum.yumRepo.YumRepository(repo_id)
        try:
            try:
                yum_repo.basecachedir = self.working_dir
                yum_repo.base_persistdir = self.working_dir
                yum_repo.cache = 0
                yum_repo.metadata_expire = 0
                yum_repo.baseurl = [feed_url]
                yum_repo.baseurlSetup()
                self.assertFalse(os.path.exists(expected_dir))
                yum_repo.dirSetup()
            except Exception, e:
                pass
                #traceback.print_exc(file=sys.stdout)
        finally:
            yum_repo.close()
        self.assertFalse(os.path.exists(expected_dir))

