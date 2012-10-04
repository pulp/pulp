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
import threading
import time
import unittest
from uuid import uuid4
import importer_mocks

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/importers/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/distributors/")

from iso_distributor.groupdistributor import GroupISODistributor, TYPE_ID_DISTRIBUTOR_ISO,\
    TYPE_ID_RPM, TYPE_ID_SRPM, TYPE_ID_DRPM, TYPE_ID_ERRATA, TYPE_ID_DISTRO, TYPE_ID_PKG_CATEGORY, TYPE_ID_PKG_GROUP
from iso_distributor.exporter import RepoExporter
from iso_distributor.generate_iso import GenerateIsos
from iso_distributor import iso_util
from yum_importer import importer_rpm
from yum_importer import errata, distribution
from pulp.plugins.model import Repository, Unit, RepositoryGroup
from pulp_rpm.repo_auth.repo_cert_utils import M2CRYPTO_HAS_CRL_SUPPORT
import distributor_mocks
import rpm_support_base

class TestGroupISODistributor(rpm_support_base.PulpRPMTests):

    def setUp(self):
        super(TestGroupISODistributor, self).setUp()
        self.init()

    def tearDown(self):
        super(TestGroupISODistributor, self).tearDown()
        self.clean()

    def init(self):
        self.temp_dir = tempfile.mkdtemp()
        #pkg_dir is where we simulate units actually residing
        self.pkg_dir = os.path.join(self.temp_dir, "packages")
        os.makedirs(self.pkg_dir)
        #distro_dir is where we simulate units actually residing
        self.distro_dir = os.path.join(self.temp_dir, "distribution")
        os.makedirs(self.distro_dir)
        #publish_dir simulates /var/lib/pulp/published
        self.http_publish_dir = os.path.join(self.temp_dir, "publish", "http", "isos")
        os.makedirs(self.http_publish_dir)

        self.https_publish_dir = os.path.join(self.temp_dir, "publish", "https", "isos")
        os.makedirs(self.https_publish_dir)

        self.repo_working_dir = os.path.join(self.temp_dir, "repo_working_dir")
        os.makedirs(self.repo_working_dir)

        self.group_working_dir = os.path.join(self.temp_dir, "group_working_dir")
        os.makedirs(self.group_working_dir)

        self.repo_iso_working_dir = os.path.join(self.temp_dir, "repo_working_dir", "isos")
        os.makedirs(self.repo_iso_working_dir)

        self.data_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), "./data"))

    def clean(self):
        shutil.rmtree(self.temp_dir)

    def test_metadata(self):
        metadata = GroupISODistributor.metadata()
        self.assertEquals(metadata["id"], TYPE_ID_DISTRIBUTOR_ISO)
        for type in [TYPE_ID_RPM, TYPE_ID_SRPM, TYPE_ID_DRPM, TYPE_ID_ERRATA, TYPE_ID_DISTRO,
                     TYPE_ID_PKG_CATEGORY, TYPE_ID_PKG_GROUP]:
            self.assertTrue(type in metadata["types"])

    def test_validate_config(self):
        distributor = GroupISODistributor()
        repo = mock.Mock(spec=Repository)
        repo.id = "testrepo"
        http = "true"
        https = False
        config = distributor_mocks.get_basic_config(http=http, https=https)
        state, msg = distributor.validate_config(repo, config, [])
        self.assertFalse(state)

        http = True
        config = distributor_mocks.get_basic_config(http=http, https=https)
        state, msg = distributor.validate_config(repo, config, [])
        self.assertTrue(state)

        http = True
        https = "False"
        relative_url = "test_path"
        config = distributor_mocks.get_basic_config(http=http, https=https)
        state, msg = distributor.validate_config(repo, config, [])
        self.assertFalse(state)

        https = True
        config = distributor_mocks.get_basic_config(http=http, https=https)
        state, msg = distributor.validate_config(repo, config, [])
        self.assertTrue(state)

        http = True
        https = False
        relative_url = "test_path"
        skip_content_types = "fake"
        config = distributor_mocks.get_basic_config(http=http, https=https,
            skip=skip_content_types)
        state, msg = distributor.validate_config(repo, config, [])
        self.assertFalse(state)

        skip_content_types = []
        config = distributor_mocks.get_basic_config(http=http, https=https,
            skip=skip_content_types)
        state, msg = distributor.validate_config(repo, config, [])
        self.assertTrue(state)

        # test invalid iso prefix
        config = distributor_mocks.get_basic_config(http=True, https=False, iso_prefix="my_iso*_name_/")
        state, msg = distributor.validate_config(repo, config, [])
        self.assertFalse(state)
        # test valid iso prefix
        config = distributor_mocks.get_basic_config(http=True, https=False, iso_prefix="My_iso_name-01")
        state, msg = distributor.validate_config(repo, config, [])
        self.assertTrue(state)

        invalid_config="dummy"
        config = distributor_mocks.get_basic_config(invalid_config)
        state, msg = distributor.validate_config(repo, config, [])
        self.assertFalse(state)

        http_publish_dir = self.http_publish_dir
        config = distributor_mocks.get_basic_config(http=http, https=https,
            http_publish_dir=http_publish_dir)
        state, msg = distributor.validate_config(repo, config, [])
        self.assertTrue(state)

        http_publish_dir = "test"
        config = distributor_mocks.get_basic_config(http=http, https=https,
            http_publish_dir=http_publish_dir)
        state, msg = distributor.validate_config(repo, config, [])
        self.assertFalse(state)

        https_publish_dir = self.https_publish_dir
        config = distributor_mocks.get_basic_config(http=http, https=https,
            https_publish_dir=https_publish_dir)
        state, msg = distributor.validate_config(repo, config, [])
        self.assertTrue(state)

        https_publish_dir = "test"
        config = distributor_mocks.get_basic_config(http=http, https=https,
            https_publish_dir=https_publish_dir)
        state, msg = distributor.validate_config(repo, config, [])
        self.assertFalse(state)

        if not M2CRYPTO_HAS_CRL_SUPPORT:
            return
        http = True
        https = False
        relative_url = "test_path"
        auth_cert = "fake"
        config = distributor_mocks.get_basic_config(http=http, https=https,
            https_ca=auth_cert)
        state, msg = distributor.validate_config(repo, config, [])
        self.assertFalse(state)

        auth_cert = open(os.path.join(self.data_dir, "cert.crt")).read()
        config = distributor_mocks.get_basic_config(http=http, https=https,
            https_ca=auth_cert)
        print auth_cert
        state, msg = distributor.validate_config(repo, config, [])
        self.assertTrue(state)

    def test_group_publish_isos(self):
        feed_url = "file://%s/pulp_unittest/" % self.data_dir
        repo_1 = mock.Mock(spec=Repository)
        repo_1.id = "test_repo_for_export_1"
        repo_1.working_dir = self.repo_working_dir
        repo_1.checksumtype = 'sha'
        repo_2 = mock.Mock(spec=Repository)
        repo_2.id = "test_repo_for_export_2"
        repo_2.working_dir = self.repo_working_dir
        repo_2.checksumtype = 'sha'
        sync_conduit = importer_mocks.get_sync_conduit(type_id=TYPE_ID_RPM, existing_units=[], pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        importerRPM = importer_rpm.ImporterRPM()
        status, summary, details = importerRPM.sync(repo_1, sync_conduit, config)
        status, summary, details = importerRPM.sync(repo_2, sync_conduit, config)
        unit_key_a = {'id' : '','name' :'pulp-dot-2.0-test', 'version' :'0.1.2', 'release' : '1.fc11', 'epoch':'0', 'arch' : 'x86_64', 'checksumtype' : 'sha256',
                      'checksum': '435d92e6c09248b501b8d2ae786f92ccfad69fab8b1bc774e2b66ff6c0d83979', 'type_id' : 'rpm'}
        unit_a = Unit(TYPE_ID_RPM, unit_key_a, {'updated' : ''}, '')
        unit_a.storage_path = "%s/pulp-dot-2.0-test/0.1.2/1.fc11/x86_64/435d92e6c09248b501b8d2ae786f92ccfad69fab8b1bc774e2b66ff6c0d83979/pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm" % self.pkg_dir
        unit_key_b = {'id' : '', 'name' :'pulp-test-package', 'version' :'0.2.1', 'release' :'1.fc11', 'epoch':'0','arch' : 'x86_64', 'checksumtype' :'sha256',
                      'checksum': '4dbde07b4a8eab57e42ed0c9203083f1d61e0b13935d1a569193ed8efc9ecfd7', 'type_id' : 'rpm', }
        unit_b = Unit(TYPE_ID_RPM, unit_key_b, {'updated' : ''}, '')
        unit_b.storage_path = "%s/pulp-test-package/0.2.1/1.fc11/x86_64/4dbde07b4a8eab57e42ed0c9203083f1d61e0b13935d1a569193ed8efc9ecfd7/pulp-test-package-0.2.1-1.fc11.x86_64.rpm" % self.pkg_dir
        unit_key_c = {'id' : '', 'name' :'pulp-test-package', 'version' :'0.3.1', 'release' :'1.fc11', 'epoch':'0','arch' : 'x86_64', 'checksumtype' :'sha256',
                      'checksum': '6bce3f26e1fc0fc52ac996f39c0d0e14fc26fb8077081d5b4dbfb6431b08aa9f', 'type_id' : 'rpm', }
        unit_c = Unit(TYPE_ID_RPM, unit_key_c, {'updated' : ''}, '')
        unit_c.storage_path =  "%s/pulp-test-package/0.3.1/1.fc11/x86_64/6bce3f26e1fc0fc52ac996f39c0d0e14fc26fb8077081d5b4dbfb6431b08aa9f/pulp-test-package-0.3.1-1.fc11.x86_64.rpm" % self.pkg_dir
        existing_units = []
        for unit in [unit_a, unit_b, unit_c]:
            existing_units.append(unit)
        sync_conduit = importer_mocks.get_sync_conduit(type_id=TYPE_ID_RPM, existing_units=existing_units, pkg_dir=self.pkg_dir)
        importerErrata = errata.ImporterErrata()
        importerErrata.sync(repo_1, sync_conduit, config)
        importerErrata.sync(repo_2, sync_conduit, config)

        repo_group = mock.Mock(spec=RepositoryGroup)
        repo_group.id = "test_group"
        repo_group.repo_ids = [repo_1.id, repo_2.id]
        repo_group.working_dir = self.group_working_dir
        global progress_status
        progress_status = None
        def set_progress(progress):
            global progress_status
            progress_status = progress
        publish_conduit = distributor_mocks.get_publish_conduit(existing_units=existing_units, pkg_dir=self.pkg_dir)
        config = distributor_mocks.get_basic_config(https_publish_dir=self.https_publish_dir, http_publish_dir=self.http_publish_dir,
            generate_metadata=True, http=True, https=False, iso_prefix="test-isos")
        distributor = GroupISODistributor()
        def cleanup(repo_working_dir):
            return
        iso_util.cleanup_working_dir.cleanup = mock.Mock()
        iso_util.cleanup_working_dir.side_effect = cleanup
        publish_conduit.set_progress = mock.Mock()
        publish_conduit.set_progress.side_effect = set_progress
        distributor.publish_group(repo_group, publish_conduit, config)
        self.assertTrue("isos" in progress_status)
        self.assertTrue(progress_status["isos"].has_key("state"))
        self.assertEqual(progress_status["isos"]["state"], "FINISHED")

        self.assertTrue(os.path.exists("%s/%s" % (self.http_publish_dir, repo_group.id)))
        self.assertEquals(len(os.listdir(self.https_publish_dir)), 0)
        isos_list = os.listdir("%s/%s" % (self.http_publish_dir, repo_group.id))
        print isos_list
        self.assertEqual(len(isos_list), 1)
        # make sure the iso name defaults to repoid
        self.assertTrue( isos_list[0].startswith("test-isos"))

    def test_publish_progress(self):
        global progress_status
        progress_status = None
        group_progress_status = None
        def set_progress(progress):
            global progress_status
            progress_status = progress
        PROGRESS_FIELDS = ["num_success", "num_error", "items_left", "items_total", "error_details"]
        publish_conduit = distributor_mocks.get_publish_conduit(pkg_dir=self.pkg_dir)
        config = distributor_mocks.get_basic_config(https_publish_dir=self.https_publish_dir, http_publish_dir=self.http_publish_dir,
            generate_metadata=True, http=True, https=False)
        distributor = GroupISODistributor()
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.repo_working_dir
        repo.id = "test_progress_sync"
        repo_group = mock.Mock(spec=RepositoryGroup)
        repo_group.id = "test_group"
        repo_group.repo_ids = [repo.id,]
        repo_group.working_dir = self.group_working_dir
        publish_conduit.set_progress = mock.Mock()
        publish_conduit.set_progress.side_effect = set_progress
        distributor.publish_group(repo_group, publish_conduit, config)
        print distributor.group_progress_status
        self.assertTrue(progress_status is not None)
        self.assertEqual(progress_status['group-id'], repo_group.id)
        self.assertTrue("rpms" in progress_status['repositories'][repo.id])
        self.assertTrue(progress_status['repositories'][repo.id]["rpms"].has_key("state"))
        self.assertEqual(progress_status['repositories'][repo.id]["rpms"]["state"], "FINISHED")
        for field in PROGRESS_FIELDS:
            self.assertTrue(field in progress_status['repositories'][repo.id]["rpms"])

        self.assertTrue("distribution" in progress_status['repositories'][repo.id])
        self.assertTrue(progress_status['repositories'][repo.id]["distribution"].has_key("state"))
        self.assertEqual(progress_status['repositories'][repo.id]["distribution"]["state"], "FINISHED")
        for field in PROGRESS_FIELDS:
            self.assertTrue(field in progress_status['repositories'][repo.id]["distribution"])

        self.assertTrue("errata" in progress_status['repositories'][repo.id])
        self.assertTrue(progress_status['repositories'][repo.id]["errata"].has_key("state"))
        self.assertEqual(progress_status['repositories'][repo.id]["errata"]["state"], "FINISHED")

        self.assertTrue("isos" in progress_status)
        self.assertTrue(progress_status["isos"].has_key("state"))
        self.assertEqual(progress_status["isos"]["state"], "FINISHED")
        ISO_PROGRESS_FIELDS = ["num_success", "num_error", "items_left", "items_total", "error_details", "written_files", "current_file", "size_total", "size_left"]
        for field in ISO_PROGRESS_FIELDS:
            self.assertTrue( field in progress_status["isos"])

        self.assertTrue("publish_http" in progress_status)
        self.assertEqual(progress_status["publish_http"]["state"], "FINISHED")
        self.assertTrue("publish_https" in progress_status)
        self.assertEqual(progress_status["publish_https"]["state"], "SKIPPED")
