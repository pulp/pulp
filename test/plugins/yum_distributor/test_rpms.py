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
import time
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../plugins/importers/yum_importer/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../plugins/distributors/yum_distributor/")
from distributor import YumDistributor, YUM_DISTRIBUTOR_TYPE_ID, \
        REQUIRED_CONFIG_KEYS, OPTIONAL_CONFIG_KEYS, RPM_TYPE_ID, SRPM_TYPE_ID

from pulp.server.content.plugins.model import Repository, Unit

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../yum_importer")
import importer_mocks

class TestRPMs(unittest.TestCase):

    def setUp(self):
        super(TestRPMs, self).setUp()
        self.init()

    def tearDown(self):
        super(TestRPMs, self).tearDown()
        self.clean()

    def init(self):
        self.temp_dir = tempfile.mkdtemp()

    def clean(self):
        shutil.rmtree(self.temp_dir)

    def test_metadata(self):
        metadata = YumDistributor.metadata()
        self.assertEquals(metadata["id"], YUM_DISTRIBUTOR_TYPE_ID)
        self.assertTrue(RPM_TYPE_ID in metadata["types"])
        self.assertTrue(SRPM_TYPE_ID in metadata["types"])

    def test_validate_config(self):
        repo = mock.Mock(spec=Repository)
        distributor = YumDistributor()
        # Confirm that required keys are successful
        req_kwargs = {}
        for arg in REQUIRED_CONFIG_KEYS:
            req_kwargs[arg] = "sample_value"
        config = importer_mocks.get_basic_config(**req_kwargs)
        state, msg = distributor.validate_config(repo, config)
        self.assertTrue(state)
        # Confirm required and optional are successful
        optional_kwargs = dict(req_kwargs)
        for arg in OPTIONAL_CONFIG_KEYS:
            optional_kwargs[arg] = "sample_value"
        config = importer_mocks.get_basic_config(**optional_kwargs)
        state, msg = distributor.validate_config(repo, config)
        self.assertTrue(state)

        # Confirm an extra key fails
        optional_kwargs["extra_arg_not_used"] = "sample_value"
        config = importer_mocks.get_basic_config(**optional_kwargs)
        state, msg = distributor.validate_config(repo, config)
        self.assertFalse(state)
        self.assertTrue("extra_arg_not_used" in msg)

        # Confirm missing a required fails
        del optional_kwargs["extra_arg_not_used"]
        config = importer_mocks.get_basic_config(**optional_kwargs)
        state, msg = distributor.validate_config(repo, config)
        self.assertTrue(state)

        del optional_kwargs["relative_url"]
        config = importer_mocks.get_basic_config(**optional_kwargs)
        state, msg = distributor.validate_config(repo, config)
        self.assertFalse(state)
        self.assertTrue("relative_url" in msg)


    def test_basic_publish(self):
        pass
        # Include a test repo that has: rpms, drpms, errata, and srpms
