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

from pulp.server.content.plugins.model import Repository

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../yum_importer")
import distributor_mocks
import metadata
class TestMetadata(unittest.TestCase):

    def setUp(self):
        super(TestMetadata, self).setUp()
        self.init()

    def tearDown(self):
        super(TestMetadata, self).tearDown()
        self.clean()

    def init(self):
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), "../data"))
        self.repodata_dir = os.path.join(self.data_dir, "test_repo_metadata/repodata/")

    def clean(self):
        shutil.rmtree(self.temp_dir)
        if os.path.exists(self.repodata_dir):
            shutil.rmtree(self.repodata_dir)

    def test_generate_metadata(self):
        mock_repo = mock.Mock(spec=Repository)
        mock_repo.id = "test_repo"
        mock_repo.scratchpad = {"checksum_type" : "sha"}
        mock_repo.working_dir = os.path.join(self.data_dir, "test_repo_metadata")
        # Confirm required and optional are successful
        optional_kwargs = {"generate_metadata" :  1}
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        mock_publish_conduit = distributor_mocks.get_publish_conduit()
        status = metadata.generate_metadata(mock_repo, mock_publish_conduit, config)
        self.assertEquals(status, True)
        optional_kwargs = {"generate_metadata" :  0}
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        mock_publish_conduit = distributor_mocks.get_publish_conduit()
        status = metadata.generate_metadata(mock_repo, mock_publish_conduit, config)
        self.assertEquals(status, False)

    def test_get_checksum_type(self):
        mock_repo = mock.Mock(spec=Repository)
        mock_repo.id = "test_repo"
        mock_repo.working_dir = os.path.join(self.data_dir, "pulp_unittest")
        optional_kwargs = {"checksum_type" :  "sha512"}
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        mock_publish_conduit = distributor_mocks.get_publish_conduit()
        _checksum_type_value = metadata.get_repo_checksum_type(mock_repo, mock_publish_conduit, config)
        print _checksum_type_value
        self.assertEquals(_checksum_type_value, optional_kwargs['checksum_type'])
        optional_kwargs = {}
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        _checksum_type_value = metadata.get_repo_checksum_type(mock_repo, mock_publish_conduit, config)
        print _checksum_type_value
        self.assertEquals(_checksum_type_value, "sha")
        mock_repo.scratchpad = None
        optional_kwargs = {}
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        mock_publish_conduit = distributor_mocks.get_publish_conduit(checksum_type=None)
        _checksum_type_value = metadata.get_repo_checksum_type(mock_repo, mock_publish_conduit, config)
        print _checksum_type_value
        self.assertEquals(_checksum_type_value, "sha256")




