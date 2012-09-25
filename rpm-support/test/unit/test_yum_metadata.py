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
import time

import mock

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/importers/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/distributors/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../common")

from pulp_rpm.yum_plugin  import metadata
from pulp.plugins.model import Repository
import distributor_mocks
import rpm_support_base
from pulp_rpm.yum_plugin.metadata import YumMetadataGenerator

class TestYumMetadataGenerate(rpm_support_base.PulpRPMTests):

    def setUp(self):
        super(TestYumMetadataGenerate, self).setUp()
        self.init()

    def tearDown(self):
        super(TestYumMetadataGenerate, self).tearDown()
        self.clean()

    def init(self):
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), "data"))

    def clean(self):
        shutil.rmtree(self.temp_dir)

    def test_yum_generate_metadata(self):
        global metadata_progress_status
        metadata_progress_status = {}

        def set_progress(progress):
            global metadata_progress_status
            metadata_progress_status = progress

        def progress_callback(type_id, status):
            metadata_progress_status[type_id] = status
            mock_publish_conduit.set_progress(metadata_progress_status)
        mock_repo = mock.Mock(spec=Repository)
        mock_repo.id = "test_repo"
        repo_scratchpad = {"checksum_type" : "sha", "repodata" : {}}
        mock_repo.working_dir = os.path.join(self.temp_dir, "test_yum_repo_metadata")
        # Confirm required and optional are successful
        units_to_write= mock.Mock()
        units_to_write.metadata = {}
        units_to_write.metadata["repodata"] = {}
        units_to_write.metadata["repodata"]["primary"] = """<package type="rpm"><name>feedless</name><arch>noarch</arch><version epoch="0" ver="1.0" rel="1"/><checksum type="sha" pkgid="YES">c1181097439ae4c69793c91febd8513475fb7ed6</checksum><summary>dummy testing pkg</summary><description>A dumb 1Mb pkg.</description><packager/><url/><time file="1299184404" build="1299168170"/><size package="1050973" installed="2097152" archive="1048976"/><location href="feedless-1.0-1.noarch.rpm"/><format><rpm:license>GPLv2</rpm:license><rpm:vendor/><rpm:group>Application</rpm:group><rpm:buildhost>pulp-qe-rhel5.usersys.redhat.com</rpm:buildhost><rpm:sourcerpm>feedless-1.0-1.src.rpm</rpm:sourcerpm><rpm:header-range start="456" end="1846"/><rpm:provides><rpm:entry name="feedless" flags="EQ" epoch="0" ver="1.0" rel="1"/></rpm:provides><rpm:requires><rpm:entry name="rpmlib(CompressedFileNames)" flags="LE" epoch="0" ver="3.0.4" rel="1" pre="1"/><rpm:entry name="rpmlib(PayloadFilesHavePrefix)" flags="LE" epoch="0" ver="4.0" rel="1" pre="1"/></rpm:requires></format></package>"""
        units_to_write.metadata["repodata"]["filelists"] = """<package pkgid="c1181097439ae4c69793c91febd8513475fb7ed6" name="feedless" arch="noarch"><version epoch="0" ver="1.0" rel="1"/><file>/tmp/rpm_test/feedless/key</file><file type="dir">/tmp/rpm_test/feedless</file></package>"""
        units_to_write.metadata["repodata"]["other"] = """<package pkgid="c1181097439ae4c69793c91febd8513475fb7ed6" name="feedless" arch="noarch"><version epoch="0" ver="1.0" rel="1"/></package>"""

        optional_kwargs = {"use_createrepo" : False}
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        mock_publish_conduit = distributor_mocks.get_publish_conduit()
        mock_publish_conduit.set_progress = mock.Mock()
        mock_publish_conduit.set_progress.side_effect = set_progress
        status, errors = metadata.generate_yum_metadata(mock_repo.working_dir, [units_to_write], config, progress_callback=progress_callback, repo_scratchpad=repo_scratchpad)
        self.assertEquals(status, True)
        self.assertEquals(metadata_progress_status['metadata']['state'], "FINISHED")

    def test_cancel_generate_repodata(self):
        global metadata_progress_status
        metadata_progress_status = {}

        def set_progress(progress):
            global metadata_progress_status
            metadata_progress_status = progress

        def progress_callback(type_id, status):
            metadata_progress_status[type_id] = status
            mock_publish_conduit.set_progress(metadata_progress_status)
        mock_repo = mock.Mock(spec=Repository)
        mock_repo.id = "test_repo"
        mock_repo.scratchpad = {"checksum_type" : "sha"}
        mock_repo.working_dir = os.path.join(self.temp_dir, "test_yum_repo_metadata")
        # Confirm required and optional are successful
        units_to_write= mock.Mock()
        units_to_write.metadata = {}
        units_to_write.metadata["repodata"] = {}
        repo_scratchpad = {"checksum_type" : "sha", "repodata" : {}}
        optional_kwargs = {}
        config = distributor_mocks.get_basic_config(**optional_kwargs)
        mock_publish_conduit = distributor_mocks.get_publish_conduit()
        mock_publish_conduit.set_progress = mock.Mock()
        mock_publish_conduit.set_progress.side_effect = set_progress

        status, errors = metadata.generate_yum_metadata(mock_repo.working_dir, [units_to_write], config, progress_callback=progress_callback, is_cancelled=True, repo_scratchpad=repo_scratchpad)
        self.assertEquals(status, False)
        self.assertEquals(metadata_progress_status['metadata']['state'], "CANCELED")

