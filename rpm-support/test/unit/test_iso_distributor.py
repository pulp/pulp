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

from iso_distributor.distributor import ISODistributor, TYPE_ID_DISTRIBUTOR_ISO,\
    TYPE_ID_RPM, TYPE_ID_SRPM, TYPE_ID_DRPM, TYPE_ID_ERRATA, TYPE_ID_DISTRO, TYPE_ID_PKG_CATEGORY, TYPE_ID_PKG_GROUP
from yum_importer import importer_rpm
from yum_importer import errata, distribution
from pulp.plugins.model import RelatedRepository, Repository, Unit
from pulp.plugins.config import PluginCallConfiguration
from pulp_rpm.yum_plugin import util, updateinfo
import distributor_mocks
import rpm_support_base

class TestISODistributor(rpm_support_base.PulpRPMTests):

    def setUp(self):
        super(TestISODistributor, self).setUp()
        self.init()

    def tearDown(self):
        super(TestISODistributor, self).tearDown()
#        self.clean()

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

        self.repo_iso_working_dir = os.path.join(self.temp_dir, "repo_working_dir", "isos")
        os.makedirs(self.repo_iso_working_dir)

        self.data_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), "./data"))

    def clean(self):
        shutil.rmtree(self.temp_dir)

    def test_metadata(self):
        metadata = ISODistributor.metadata()
        self.assertEquals(metadata["id"], TYPE_ID_DISTRIBUTOR_ISO)
        for type in [TYPE_ID_RPM, TYPE_ID_SRPM, TYPE_ID_DRPM, TYPE_ID_ERRATA, TYPE_ID_DISTRO,
                     TYPE_ID_PKG_CATEGORY, TYPE_ID_PKG_GROUP]:
            self.assertTrue(type in metadata["types"])

    def test_export_rpm(self):
        feed_url = "file://%s/test_repo_for_export/" % (self.data_dir)
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.repo_working_dir
        repo.id = "test_repo_for_export"
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=[], pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        importerRPM = importer_rpm.ImporterRPM()
        status, summary, details = importerRPM.sync(repo, sync_conduit, config)
        self.assertTrue(summary is not None)
        self.assertTrue(details is not None)
        self.assertTrue(status)
        unit_key_a = {'id' : '','name' :'pulp-dot-2.0-test', 'version' :'0.1.2', 'release' : '1.fc11', 'epoch':'0', 'arch' : 'x86_64', 'checksumtype' : 'sha256',
                      'checksum': '435d92e6c09248b501b8d2ae786f92ccfad69fab8b1bc774e2b66ff6c0d83979', 'type_id' : 'rpm'}
        unit_a = Unit(TYPE_ID_RPM, unit_key_a, {}, '')
        unit_a.storage_path = "%s/pulp-dot-2.0-test/0.1.2/1.fc11/x86_64/435d92e6c09248b501b8d2ae786f92ccfad69fab8b1bc774e2b66ff6c0d83979/pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm" % self.pkg_dir
        unit_key_b = {'id' : '', 'name' :'pulp-test-package', 'version' :'0.2.1', 'release' :'1.fc11', 'epoch':'0','arch' : 'x86_64', 'checksumtype' :'sha256',
                      'checksum': '4dbde07b4a8eab57e42ed0c9203083f1d61e0b13935d1a569193ed8efc9ecfd7', 'type_id' : 'rpm', }
        unit_b = Unit(TYPE_ID_RPM, unit_key_b, {}, '')
        unit_b.storage_path = "%s/pulp-test-package/0.2.1/1.fc11/x86_64/4dbde07b4a8eab57e42ed0c9203083f1d61e0b13935d1a569193ed8efc9ecfd7/pulp-test-package-0.2.1-1.fc11.x86_64.rpm" % self.pkg_dir
        unit_key_c = {'id' : '', 'name' :'pulp-test-package', 'version' :'0.3.1', 'release' :'1.fc11', 'epoch':'0','arch' : 'x86_64', 'checksumtype' :'sha256',
                      'checksum': '6bce3f26e1fc0fc52ac996f39c0d0e14fc26fb8077081d5b4dbfb6431b08aa9f', 'type_id' : 'rpm', }
        unit_c = Unit(TYPE_ID_RPM, unit_key_c, {}, '')
        unit_c.storage_path =  "%s/pulp-test-package/0.3.1/1.fc11/x86_64/6bce3f26e1fc0fc52ac996f39c0d0e14fc26fb8077081d5b4dbfb6431b08aa9f/pulp-test-package-0.3.1-1.fc11.x86_64.rpm" % self.pkg_dir
        existing_units = []
        for unit in [unit_a, unit_b, unit_c]:
            existing_units.append(unit)
        symlink_dir = "%s/%s" % (self.repo_working_dir, "isos")
        iso_distributor = ISODistributor()
        publish_conduit = distributor_mocks.get_publish_conduit(existing_units=existing_units, pkg_dir=self.pkg_dir)
        config = distributor_mocks.get_basic_config(http_publish_dir=self.http_publish_dir)
        print symlink_dir
        status, errors = iso_distributor._export_rpms(existing_units, symlink_dir)
        print status, errors
        self.assertTrue(status)
        self.assertEquals(len(os.listdir(symlink_dir)), 3)

    def test_errata_export(self):
        feed_url = "file://%s/test_errata_local_sync/" % self.data_dir
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.repo_working_dir
        repo.id = "test_errata_local_sync"
        repo.checksumtype = 'sha'
        sync_conduit = importer_mocks.get_sync_conduit(type_id=TYPE_ID_RPM, existing_units=[], pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        importerRPM = importer_rpm.ImporterRPM()
        status, summary, details = importerRPM.sync(repo, sync_conduit, config)
        metadata = {}
        unit_key_a = {'id' : '','name' :'patb', 'version' :'0.1', 'release' : '2', 'epoch':'0', 'arch' : 'x86_64', 'checksumtype' : 'md5',
                      'checksum': 'f3c197a29d9b66c5b65c5d62b25db5b4'}
        unit_key_b = {'id' : '', 'name' :'emoticons', 'version' :'0.1', 'release' :'2', 'epoch':'0','arch' : 'x86_64', 'checksumtype' :'md5',
                      'checksum' : '366bb5e73a5905eacb82c96e0578f92b'}

        existing_units = []
        for unit in [unit_key_a, unit_key_b]:
            existing_units.append(Unit(TYPE_ID_RPM, unit, metadata, ''))
        sync_conduit = importer_mocks.get_sync_conduit(type_id=TYPE_ID_RPM, existing_units=existing_units, pkg_dir=self.pkg_dir)
        importerErrata = errata.ImporterErrata()
        status, summary, details = importerErrata.sync(repo, sync_conduit, config)
        unit_key = dict()
        unit_key['id'] = "RHEA-2010:9999"
        mdata = { 'description'  : "test",
                     'from_str': 'security@redhat.com',
                    'issued': '2010-03-30 08:07:30',
                    'pkglist': [{'name': 'RHEL Virtualization (v. 5 for 32-bit x86)',
                            'packages': [{'arch': 'x86_64',
                                        'epoch': '0',
                                        'filename': 'patb-0.1-2.x86_64.rpm',
                                        'name': 'patb',
                                        'release': '2',
                                        'src': '',
                                        'sum': ('md5',
                                                'f3c197a29d9b66c5b65c5d62b25db5b4'),
                                        'version': '0.1'},
                                        {'arch': 'x86_64',
                                        'epoch': '0',
                                        'filename': 'emoticons-0.1-2.x86_64.rpm',
                                        'name': 'emoticons',
                                        'release': '2',
                                        'src': '',
                                        'sum': ('md5',
                                                '366bb5e73a5905eacb82c96e0578f92b'),
                                        'version': '0.1'}],
                            'short': 'rhel-i386-server-vt-5'}],
                    'pushcount': 1,
                    'reboot_suggested': False,
                    'references': [],
                    'release': '',
                    'rights': '',
                     'status': 'final',
                    'summary': '',
                    'title': 'emoticons enhancement fix and enhancement update',
                     'updated': '2010-03-30 08:07:30',
        'version': '1',
        'type' : 'enhancement',
        'severity' : 'Low',
        'solution' : ''}
        errata_unit = [Unit(TYPE_ID_ERRATA, unit_key, mdata, '')]
        symlink_dir = "%s/%s" % (self.repo_working_dir, repo.id)
        iso_distributor = ISODistributor()
        publish_conduit = distributor_mocks.get_publish_conduit(existing_units=existing_units, pkg_dir=self.pkg_dir)
        config = distributor_mocks.get_basic_config(http_publish_dir=self.http_publish_dir)
        print symlink_dir
        rpm_units = iso_distributor._get_errata_rpms(errata_unit, existing_units)
        print "RPMS in ERRATA",rpm_units
        iso_distributor._export_rpms(rpm_units, self.repo_working_dir)
        status, errors = iso_distributor._export_errata(errata_unit, symlink_dir)
        self.assertTrue(os.path.exists("%s/%s" % (symlink_dir, "updateinfo.xml")))
        self.assertTrue(status)
        ftypes = util.get_repomd_filetypes("%s/%s" % (symlink_dir, "repodata/repomd.xml"))
        print ftypes
        self.assertTrue("updateinfo" in ftypes)

    def test_distribution_exports(self):
        feed_url = "file://%s/pulp_unittest/" % self.data_dir
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.repo_working_dir
        repo.id = "pulp_unittest"
        repo.checksumtype = 'sha'
        sync_conduit = importer_mocks.get_sync_conduit(type_id=TYPE_ID_RPM, existing_units=[], pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        importerRPM = importer_rpm.ImporterRPM()
        status, summary, details = importerRPM.sync(repo, sync_conduit, config)
        dunit_key = {}
        dunit_key['id'] = "ks-TestFamily-TestVariant-16-x86_64"
        dunit_key['version'] = "16"
        dunit_key['arch'] = "x86_64"
        dunit_key['family'] = "TestFamily"
        dunit_key['variant'] = "TestVariant"
        metadata = { "files" : [{"checksumtype" : "sha256", 	"relativepath" : "images/fileA.txt", 	"fileName" : "fileA.txt",
                    "downloadurl" : "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest//images/fileA.txt",
                    "item_type" : "tree_file",
                    "savepath" : "%s/testr1/images" % self.repo_working_dir,
                    "checksum" : "22603a94360ee24b7034c74fa13d70dd122aa8c4be2010fc1361e1e6b0b410ab",
                    "filename" : "fileA.txt",
                    "pkgpath" : "%s/ks-TestFamily-TestVariant-16-x86_64/images" % self.pkg_dir,
                    "size" : 0 },
                { 	"checksumtype" : "sha256", 	"relativepath" : "images/fileB.txt", 	"fileName" : "fileB.txt",
                    "downloadurl" : "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest//images/fileB.txt",
                    "item_type" : "tree_file",
                    "savepath" : "%s/testr1/images" % self.repo_working_dir,
                    "checksum" : "8dc89e9883c098443f6616e60a8e489254bf239eeade6e4b4943b7c8c0c345a4",
                    "filename" : "fileB.txt",
                    "pkgpath" : "%s/ks-TestFamily-TestVariant-16-x86_64/images" % self.pkg_dir, 	"size" : 0 },
                { 	"checksumtype" : "sha256", 	"relativepath" : "images/fileC.iso", 	"fileName" : "fileC.iso",
                    "downloadurl" : "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest//images/fileC.iso",
                    "item_type" : "tree_file",
                    "savepath" : "%s/testr1/images" % self.repo_working_dir,
                    "checksum" : "099f2bafd533e97dcfee778bc24138c40f114323785ac1987a0db66e07086f74",
                    "filename" : "fileC.iso",
                    "pkgpath" : "%s/ks-TestFamily-TestVariant-16-x86_64/images" % self.pkg_dir, 	"size" : 0 } ],}
        distro_unit = Unit(distribution.TYPE_ID_DISTRO, dunit_key, metadata, '')
        distro_unit.storage_path = "%s/ks-TestFamily-TestVariant-16-x86_64" % self.pkg_dir
        symlink_dir = "%s/%s" % (self.repo_working_dir, "isos")
        iso_distributor = ISODistributor()
        publish_conduit = distributor_mocks.get_publish_conduit(existing_units=[distro_unit], pkg_dir=self.pkg_dir)
        config = distributor_mocks.get_basic_config(http_publish_dir=self.http_publish_dir)
        status, errors = iso_distributor._export_distributions([distro_unit], symlink_dir)
        print status, errors
        self.assertTrue(status)
        for file in metadata['files']:
            print os.path.isfile("%s/%s" % (symlink_dir, file['relativepath']))
            self.assertTrue(os.path.isfile("%s/%s" % (symlink_dir, file['relativepath'])))

    def test_repo_export_isos(self):
        feed_url = "file://%s/pulp_unittest/" % self.data_dir
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.repo_working_dir
        repo.id = "pulp_unittest"
        repo.checksumtype = 'sha'
        sync_conduit = importer_mocks.get_sync_conduit(type_id=TYPE_ID_RPM, existing_units=[], pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        importerRPM = importer_rpm.ImporterRPM()
        status, summary, details = importerRPM.sync(repo, sync_conduit, config)
        unit_key_a = {'id' : '','name' :'pulp-dot-2.0-test', 'version' :'0.1.2', 'release' : '1.fc11', 'epoch':'0', 'arch' : 'x86_64', 'checksumtype' : 'sha256',
                      'checksum': '435d92e6c09248b501b8d2ae786f92ccfad69fab8b1bc774e2b66ff6c0d83979', 'type_id' : 'rpm'}
        unit_a = Unit(TYPE_ID_RPM, unit_key_a, {}, '')
        unit_a.storage_path = "%s/pulp-dot-2.0-test/0.1.2/1.fc11/x86_64/435d92e6c09248b501b8d2ae786f92ccfad69fab8b1bc774e2b66ff6c0d83979/pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm" % self.pkg_dir
        unit_key_b = {'id' : '', 'name' :'pulp-test-package', 'version' :'0.2.1', 'release' :'1.fc11', 'epoch':'0','arch' : 'x86_64', 'checksumtype' :'sha256',
                      'checksum': '4dbde07b4a8eab57e42ed0c9203083f1d61e0b13935d1a569193ed8efc9ecfd7', 'type_id' : 'rpm', }
        unit_b = Unit(TYPE_ID_RPM, unit_key_b, {}, '')
        unit_b.storage_path = "%s/pulp-test-package/0.2.1/1.fc11/x86_64/4dbde07b4a8eab57e42ed0c9203083f1d61e0b13935d1a569193ed8efc9ecfd7/pulp-test-package-0.2.1-1.fc11.x86_64.rpm" % self.pkg_dir
        unit_key_c = {'id' : '', 'name' :'pulp-test-package', 'version' :'0.3.1', 'release' :'1.fc11', 'epoch':'0','arch' : 'x86_64', 'checksumtype' :'sha256',
                      'checksum': '6bce3f26e1fc0fc52ac996f39c0d0e14fc26fb8077081d5b4dbfb6431b08aa9f', 'type_id' : 'rpm', }
        unit_c = Unit(TYPE_ID_RPM, unit_key_c, {}, '')
        unit_c.storage_path =  "%s/pulp-test-package/0.3.1/1.fc11/x86_64/6bce3f26e1fc0fc52ac996f39c0d0e14fc26fb8077081d5b4dbfb6431b08aa9f/pulp-test-package-0.3.1-1.fc11.x86_64.rpm" % self.pkg_dir
        existing_units = []
        for unit in [unit_a, unit_b, unit_c]:
            existing_units.append(unit)
        sync_conduit = importer_mocks.get_sync_conduit(type_id=TYPE_ID_RPM, existing_units=existing_units, pkg_dir=self.pkg_dir)
        importerErrata = errata.ImporterErrata()
        importerErrata.sync(repo, sync_conduit, config)
        repo.working_dir = "%s/%s" % (self.repo_working_dir, "export")
        iso_distributor = ISODistributor()
        publish_conduit = distributor_mocks.get_publish_conduit(existing_units=existing_units, pkg_dir=self.pkg_dir)
        # test http publish
        config = distributor_mocks.get_basic_config(http_publish_dir=self.http_publish_dir, generate_metadata=True)
        report = iso_distributor.publish_repo(repo, publish_conduit, config)
        print report
        self.assertEquals(len(os.listdir(self.http_publish_dir)), 1)

        # test http publish
        config = distributor_mocks.get_basic_config(http_publish_dir=self.http_publish_dir)
        report = iso_distributor.publish_repo(repo, publish_conduit, config)

        self.assertTrue(os.path.exists("%s/%s" % (self.http_publish_dir, repo.id)))
        isos_list = os.listdir("%s/%s" % (self.http_publish_dir, repo.id))
        self.assertEqual(len(isos_list), 1)

    def test_iso_export_by_date_range(self):
        feed_url = "file://%s/test_errata_local_sync/" % self.data_dir
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.repo_working_dir
        repo.id = "test_errata_local_sync"
        repo.checksumtype = 'sha'
        sync_conduit = importer_mocks.get_sync_conduit(type_id=TYPE_ID_RPM, existing_units=[], pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        importerRPM = importer_rpm.ImporterRPM()
        status, summary, details = importerRPM.sync(repo, sync_conduit, config)
        metadata = {}
        existing_units = []
        unit_key_a = {'id' : '','name' :'patb', 'version' :'0.1', 'release' : '2', 'epoch':'0', 'arch' : 'x86_64', 'checksumtype' : 'sha',
                      'checksum': '017c12050a97cf6095892498750c2a39d2bf535e'}
        rpm_unit_a = Unit(TYPE_ID_RPM, unit_key_a, metadata, '')
        rpm_unit_a.storage_path = "%s/patb/0.1/2/noarch/017c12050a97cf6095892498750c2a39d2bf535e/patb-0.1-2.noarch.rpm" % self.pkg_dir
        existing_units.append(rpm_unit_a)
        unit_key_b = {'id' : '', 'name' :'emoticons', 'version' :'0.1', 'release' :'2', 'epoch':'0','arch' : 'x86_64', 'checksumtype' :'sha',
                      'checksum' : '663c89b0d29bfd5479d8736b716d50eed9495dbb'}
        rpm_unit_b = Unit(TYPE_ID_RPM, unit_key_b, metadata, '')
        rpm_unit_b.storage_path = "%s/emoticons/0.1/2/noarch/663c89b0d29bfd5479d8736b716d50eed9495dbb/emoticons-0.1-2.noarch.rpm" % self.pkg_dir
        existing_units.append(rpm_unit_b)
        sync_conduit = importer_mocks.get_sync_conduit(type_id=TYPE_ID_RPM, existing_units=existing_units, pkg_dir=self.pkg_dir)
        importerErrata = errata.ImporterErrata()
        status, summary, details = importerErrata.sync(repo, sync_conduit, config)
        unit_key = dict()
        unit_key['id'] = "RHEA-2010:9999"
        mdata = { 'description'  : "test",
                     'from_str': 'security@redhat.com',
                    'issued': '2010-03-30 08:07:30',
                    'pkglist': [{'name': 'RHEL Virtualization (v. 5 for 32-bit x86)',
                            'packages': [{'arch': 'x86_64',
                                        'epoch': '0',
                                        'filename': 'patb-0.1-2.x86_64.rpm',
                                        'name': 'patb',
                                        'release': '2',
                                        'src': '',
                                        'sum': ('sha',
                                                '017c12050a97cf6095892498750c2a39d2bf535e'),
                                        'version': '0.1'},
                                        {'arch': 'x86_64',
                                        'epoch': '0',
                                        'filename': 'emoticons-0.1-2.x86_64.rpm',
                                        'name': 'emoticons',
                                        'release': '2',
                                        'src': '',
                                        'sum': ('sha',
                                                '663c89b0d29bfd5479d8736b716d50eed9495dbb'),
                                        'version': '0.1'}],
                            'short': 'rhel-i386-server-vt-5'}],
                    'pushcount': 1,
                    'reboot_suggested': False,
                    'references': [],
                    'release': '',
                    'rights': '',
                     'status': 'final',
                    'summary': '',
                    'title': 'emoticons enhancement fix and enhancement update',
                     'updated': '2010-03-30 08:07:30',
        'version': '1',
        'type' : 'enhancement',
        'severity' : 'Low',
        'solution' : ''}
        unit_key_2 = dict()
        unit_key_2['id'] = "RHEA-2008:9999"
        mdata_2 = { 'description'  : "test",
                     'from_str': 'security@redhat.com',
                    'issued': '2008-03-30 00:00:00',
                    'pkglist': [{'name': 'RHEL Virtualization (v. 5 for 32-bit x86)',
                            'packages': [{'arch': 'x86_64',
                                        'epoch': '0',
                                        'filename': 'patb-0.1-2.x86_64.rpm',
                                        'name': 'patb',
                                        'release': '2',
                                        'src': '',
                                        'sum': ('sha',
                                                '017c12050a97cf6095892498750c2a39d2bf535e'),
                                        'version': '0.1'},
                                        {'arch': 'x86_64',
                                        'epoch': '0',
                                        'filename': 'emoticons-0.1-2.x86_64.rpm',
                                        'name': 'emoticons',
                                        'release': '2',
                                        'src': '',
                                        'sum': ('sha',
                                                '663c89b0d29bfd5479d8736b716d50eed9495dbb'),
                                        'version': '0.1'}],
                            'short': 'rhel-i386-server-vt-5'}],
                    'pushcount': 1,
                    'reboot_suggested': False,
                    'references': [],
                    'release': '',
                    'rights': '',
                     'status': 'final',
                    'summary': '',
                    'title': 'emoticons enhancement fix and enhancement update',
                     'updated': '2008-03-30 00:00:00',
        'version': '1',
        'type' : 'enhancement',
        'severity' : 'Low',
        'solution' : ''}
        errata_unit = [Unit(TYPE_ID_ERRATA, unit_key, mdata, ''), Unit(TYPE_ID_ERRATA, unit_key_2,  mdata_2, '')]
        existing_units += errata_unit
        print existing_units
        repo.working_dir = "%s/%s" % (self.repo_working_dir, "export")
        iso_distributor = ISODistributor()
        publish_conduit = distributor_mocks.get_publish_conduit(existing_units=existing_units, pkg_dir=self.pkg_dir)

        # test http publish
        config = distributor_mocks.get_basic_config(http_publish_dir=self.http_publish_dir,
            start_date="2009-03-30 08:07:30", end_date="2012-03-30 08:07:30", generate_metadata=True)
        report = iso_distributor.publish_repo(repo, publish_conduit, config)
        ftypes = util.get_repomd_filetypes("%s/%s" % (repo.working_dir, "repodata/repomd.xml"))
        self.assertTrue("updateinfo" in ftypes)
        updateinfo_path = "%s/%s" % (repo.working_dir, "updateinfo.xml")
        self.assertTrue(os.path.exists(updateinfo_path))
        elist = updateinfo.get_errata(updateinfo_path)
        self.assertEquals(len(elist), 1)
        self.assertTrue(unit_key_2['id'] not in elist[0])
        self.assertEquals(elist[0]['id'], unit_key['id'])
        self.assertEquals(elist[0]['issued'], mdata['issued'])
        self.assertTrue(os.path.exists("%s/%s" % (self.http_publish_dir, repo.id)))
        isos_list = os.listdir("%s/%s" % (self.http_publish_dir, repo.id))
        self.assertEqual(len(isos_list), 1)
