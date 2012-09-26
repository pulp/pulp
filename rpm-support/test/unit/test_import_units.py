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
import pycurl
import shutil
import sys
import tempfile
import time
import unittest
import itertools

from grinder.BaseFetch import BaseFetch

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../plugins/importers/")
import importer_mocks
from yum_importer import importer_rpm
from yum_importer.importer import YumImporter
from pulp_rpm.common.ids import TYPE_ID_RPM, UNIT_KEY_RPM, TYPE_ID_IMPORTER_YUM, TYPE_ID_ERRATA, TYPE_ID_DISTRO
from pulp_rpm.yum_plugin import util

from pulp.plugins.model import Repository, Unit
import rpm_support_base

class TestImportUnits(rpm_support_base.PulpRPMTests):

    def setUp(self):
        super(TestImportUnits, self).setUp()
        self.saved_verify_exists = util.verify_exists
        self.init()

    def tearDown(self):
        super(TestImportUnits, self).tearDown()
        util.verify_exists = self.saved_verify_exists
        self.clean()

    def init(self):
        self.temp_dir = tempfile.mkdtemp()
        self.working_dir = os.path.join(self.temp_dir, "working")
        self.pkg_dir = os.path.join(self.temp_dir, "packages")
        self.data_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), "data"))

    def clean(self):
        shutil.rmtree(self.temp_dir)

    def get_files_in_dir(self, pattern, path):
        files = []
        for d,_,_ in os.walk(path):
            files.extend(glob.glob(os.path.join(d,pattern))) 
        return files

    def setup_source_repo(self):
        # Sync a sample repository to populate and setup up Source Repo
        source_repo = mock.Mock(spec=Repository)
        source_repo.id = "repo_a"
        source_repo.working_dir = os.path.join(self.working_dir, source_repo.id)
        importer = YumImporter()
        feed_url = "file://%s/pulp_unittest/" % (self.data_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=[], pkg_dir=self.pkg_dir)
        status, summary, details = importer._sync_repo(source_repo, sync_conduit, config)
        self.assertTrue(status)
        self.assertEquals(summary["packages"]["num_synced_new_rpms"], 3)
        #
        # Now we have some test data in the source repo
        #
        # Simulate what import_conduit.get_source_repos would return
        #
        source_units = []
        storage_path = '%s/pulp-dot-2.0-test/0.1.2/1.fc11/x86_64/435d92e6c09248b501b8d2ae786f92ccfad69fab8b1bc774e2b66ff6c0d83979/pulp-dot-2.0-test-0.1.2-1.fc11.x86_64.rpm' % (self.pkg_dir)
        filename = os.path.basename(storage_path)
        unit_key = {
            'name':'pulp-dot-2.0-test',
            'version':'0.1.2',
            'release':'1.fc11',
            'epoch':'0',
            'arch':'x86_64',
            'checksum':'435d92e6c09248b501b8d2ae786f92ccfad69fab8b1bc774e2b66ff6c0d83979',
            'checksumtype':'sha256',
        }
        metadata = {
            'filename':filename
        }
        source_units.append(Unit(TYPE_ID_RPM, unit_key, metadata, storage_path))
        storage_path = '%s/pulp-test-package/0.3.1/1.fc11/x86_64/6bce3f26e1fc0fc52ac996f39c0d0e14fc26fb8077081d5b4dbfb6431b08aa9f/pulp-test-package-0.3.1-1.fc11.x86_64.rpm' % (self.pkg_dir)
        filename = os.path.basename(storage_path)
        unit_key = {
            'name':'pulp-test-package',
            'version':'0.3.1',
            'release':'1.fc11',
            'epoch':'0',
            'arch':'x86_64',
            'checksum':'6bce3f26e1fc0fc52ac996f39c0d0e14fc26fb8077081d5b4dbfb6431b08aa9f',
            'checksumtype':'sha256',
        }
        metadata = {
            'filename':filename
        }
        source_units.append(Unit(TYPE_ID_RPM, unit_key, metadata, storage_path))
        storage_path = '%s/pulp-test-package/0.2.1/1.fc11/x86_64/4dbde07b4a8eab57e42ed0c9203083f1d61e0b13935d1a569193ed8efc9ecfd7/pulp-test-package-0.2.1-1.fc11.x86_64.rpm' % (self.pkg_dir)
        filename = os.path.basename(storage_path)
        unit_key = {
            'name':'pulp-test-package',
            'version':'0.2.1',
            'release':'1.fc11',
            'epoch':'0',
            'arch':'x86_64',
            'checksum':'4dbde07b4a8eab57e42ed0c9203083f1d61e0b13935d1a569193ed8efc9ecfd7',
            'checksumtype':'sha256',
        }
        metadata = {
            'filename':filename
        }
        source_units.append(Unit(TYPE_ID_RPM, unit_key, metadata, storage_path))
        # Pass in the simulated source_units to the import_conduit
        import_conduit = importer_mocks.get_import_conduit(source_units=source_units, existing_units=source_units)
        return importer, source_repo, source_units, import_conduit, config

    def test_basic_import(self):
        importer, source_repo, source_units, import_conduit, config = self.setup_source_repo()
        dest_repo = mock.Mock(spec=Repository)
        dest_repo.id = "repo_b"
        dest_repo.working_dir = os.path.join(self.working_dir, dest_repo.id)
        specific_units = []
        #  We need to test that:
        #   1) associate_unit was called on each unit type
        #   2) symlinks were created in the dest_repo working dir
        importer.import_units(source_repo, dest_repo, import_conduit, config, specific_units)
        #
        #  Test that we called import_conduit.associate_unit for each source_unit
        #  We convert the mock call_list to extract the unit argument per call
        #  Assume only one argument to import_conduit.associate_units()
        #
        associated_units = [mock_call[0][0] for mock_call in import_conduit.associate_unit.call_args_list]
        self.assertEqual(len(associated_units), len(source_units))
        for u in associated_units:
            self.assertTrue(u in source_units)

    def test_import_specific_units(self):
        importer, source_repo, source_units, import_conduit, config = self.setup_source_repo()
        dest_repo = mock.Mock(spec=Repository)
        dest_repo.id = "repo_b"
        dest_repo.working_dir = os.path.join(self.working_dir, dest_repo.id)
        specific_units = [source_units[0], source_units[1]]
        #  We need to test that:
        #   1) associate_unit was called on each unit of specific_units
        #   2) symlinks were created in the dest_repo working dir
        importer.import_units(source_repo, dest_repo, import_conduit, config, specific_units)
        #
        #  Test that we called import_conduit.associate_unit for each specific_unit
        #  We convert the mock call_list to extract the unit argument per call
        #  Assume only one argument to import_conduit.associate_units()
        #
        associated_units = [mock_call[0][0] for mock_call in import_conduit.associate_unit.call_args_list]
        self.assertEqual(len(associated_units), len(specific_units))
        for u in associated_units:
            self.assertTrue(u in specific_units)

    def test_errata_import_units(self):
        existing_units = []
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
        # REPO A (source)
        repoA = mock.Mock(spec=Repository)
        repoA.working_dir = self.data_dir
        repoA.id = "test_errata_unit_copy"
        # REPO B (target)
        repoB = mock.Mock(spec=Repository)
        repoB.working_dir = self.working_dir
        repoB.id = "repoB"
        conduit = importer_mocks.get_import_conduit(errata_unit, existing_units=existing_units)
        config = importer_mocks.get_basic_config()
        importer = YumImporter()
        # Test
        result = importer.import_units(repoA, repoB, conduit, config, errata_unit)
        # Verify
        print conduit.associate_unit.call_args_list
        associated_units = [mock_call[0][0] for mock_call in conduit.associate_unit.call_args_list]
        self.assertEqual(len(associated_units), len(errata_unit))
        for u in associated_units:
            self.assertTrue(u in errata_unit)


    def test_distribution_unit_import(self):
        existing_units = []
        dunit_key = {}
        dunit_key['id'] = "ks-TestFamily-TestVariant-16-x86_64"
        dunit_key['version'] = "16"
        dunit_key['arch'] = "x86_64"
        dunit_key['family'] = "TestFamily"
        dunit_key['variant'] = "TestVariant"
        metadata = { "files" : [{"checksumtype" : "sha256", 	"relativepath" : "images/fileA.txt", 	"fileName" : "fileA.txt",
                                 "downloadurl" : "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest//images/fileA.txt",
                                 "item_type" : "tree_file",
                                 "savepath" : "%s/testr1/images" % self.data_dir,
                                 "checksum" : "22603a94360ee24b7034c74fa13d70dd122aa8c4be2010fc1361e1e6b0b410ab",
                                 "filename" : "fileA.txt",
                                 "pkgpath" : "%s/ks-TestFamily-TestVariant-16-x86_64/images" % self.pkg_dir,
                                 "size" : 0 },
                { 	"checksumtype" : "sha256", 	"relativepath" : "images/fileB.txt", 	"fileName" : "fileB.txt",
                      "downloadurl" : "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest//images/fileB.txt",
                      "item_type" : "tree_file",
                      "savepath" : "%s/testr1/images" % self.data_dir,
                      "checksum" : "8dc89e9883c098443f6616e60a8e489254bf239eeade6e4b4943b7c8c0c345a4",
                      "filename" : "fileB.txt",
                      "pkgpath" : "%s/ks-TestFamily-TestVariant-16-x86_64/images" % self.pkg_dir, 	"size" : 0 },
                { 	"checksumtype" : "sha256", 	"relativepath" : "images/fileC.iso", 	"fileName" : "fileC.iso",
                      "downloadurl" : "http://repos.fedorapeople.org/repos/pulp/pulp/demo_repos/pulp_unittest//images/fileC.iso",
                      "item_type" : "tree_file",
                      "savepath" : "%s/testr1/images" % self.data_dir,
                      "checksum" : "099f2bafd533e97dcfee778bc24138c40f114323785ac1987a0db66e07086f74",
                      "filename" : "fileC.iso",
                      "pkgpath" : "%s/ks-TestFamily-TestVariant-16-x86_64/images" % self.pkg_dir, 	"size" : 0 } ],}
        distro_unit = [Unit(TYPE_ID_DISTRO, dunit_key, metadata, '')]
        distro_unit[0].storage_path = "%s/ks-TestFamily-TestVariant-16-x86_64" % self.pkg_dir
        existing_units += distro_unit
        # REPO A (source)
        repoA = mock.Mock(spec=Repository)
        repoA.working_dir = self.data_dir
        repoA.id = "test_distro_unit_copy"
        # REPO B (target)
        repoB = mock.Mock(spec=Repository)
        repoB.working_dir = self.working_dir
        repoB.id = "repoB"
        conduit = importer_mocks.get_import_conduit([distro_unit], existing_units=existing_units)
        config = importer_mocks.get_basic_config()
        importer = YumImporter()
        # Test
        result = importer.import_units(repoA, repoB, conduit, config, distro_unit)
        # Verify
        print conduit.associate_unit.call_args_list
        associated_units = [mock_call[0][0] for mock_call in conduit.associate_unit.call_args_list]
        self.assertEqual(len(associated_units), len(distro_unit))
        for u in associated_units:
            self.assertTrue(u in distro_unit)

class TestImportDependencies(rpm_support_base.PulpRPMTests):

    UNIT_KEY_A = {
        'id' : '',
        'name' :'pulp-server',
        'version' :'0.0.309',
        'release' : '1.fc17',
        'epoch':'0',
        'arch' : 'noarch',
        'checksumtype' : 'sha256',
        'checksum': 'ee5afa0aaf8bd2130b7f4a9b35f4178336c72e95358dd33bda8acaa5f28ea6e9',
        'type_id' : 'rpm'
    }
    UNIT_KEY_B = {
        'id' : '',
        'name' :'pulp-rpm-server',
        'version' :'0.0.309',
        'release' :'1.fc17',
        'epoch':'0',
        'arch' : 'noarch',
        'checksumtype' :'sha256',
        'checksum': '1e6c3a3bae26423fe49d26930b986e5f5ee25523c13f875dfcd4bf80f770bf56',
        'type_id' : 'rpm'
    }

    def setUp(self):
        super(TestImportDependencies, self).setUp()
        self.temp_dir = tempfile.mkdtemp()
        self.working_dir = os.path.join(self.temp_dir, "working")
        self.pkg_dir = os.path.join(self.temp_dir, "packages")
        self.data_dir = os.path.abspath(os.path.join(os.path.abspath(os.path.dirname(__file__)), "data"))

    def tearDown(self):
        super(TestImportDependencies, self).tearDown()
        self.clean()

    def clean(self):
        shutil.rmtree(self.temp_dir)
        # clean up dir created by yum's repostorage
        if os.path.exists("./test_resolve_deps"):
            shutil.rmtree("test_resolve_deps")

    def get_files_in_dir(self, pattern, path):
        files = []
        for d,_,_ in os.walk(path):
            files.extend(glob.glob(os.path.join(d,pattern)))
        return files

    def existing_units(self):
        units = []
        for unit in [self.UNIT_KEY_A, self.UNIT_KEY_B]:
            unit = Unit(TYPE_ID_RPM, unit, {}, '')
            units.append(unit)
        return units

    def test_import(self):
        # Setup
        existing_units = self.existing_units()
        # REPO A (source)
        repoA = mock.Mock(spec=Repository)
        repoA.working_dir = self.data_dir
        repoA.id = "test_resolve_deps"
        # REPO B (target)
        repoB = mock.Mock(spec=Repository)
        repoB.working_dir = self.working_dir
        repoB.id = "repoB"
        units = [Unit(TYPE_ID_RPM, self.UNIT_KEY_B, {}, '')]
        conduit = importer_mocks.get_import_conduit(units, existing_units=existing_units)
        config = importer_mocks.get_basic_config()
        importer = YumImporter()
        # Test
        result = importer.import_units(repoA, repoB, conduit, config, units)
        # Verify
        associated_units = [mock_call[0][0] for mock_call in conduit.associate_unit.call_args_list]
        self.assertEqual(len(associated_units), len(units))
        for u in associated_units:
            self.assertTrue(u in units)

    def test_import_with_dependencies(self):
        # Setup
        existing_units = self.existing_units()
        # REPO A (source)
        repoA = mock.Mock(spec=Repository)
        repoA.working_dir = self.data_dir
        repoA.id = "test_resolve_deps"
        # REPO B (target)
        repoB = mock.Mock(spec=Repository)
        repoB.working_dir = self.working_dir
        repoB.id = "repo_b"
        units = [Unit(TYPE_ID_RPM, self.UNIT_KEY_B, {}, '')]
        conduit = importer_mocks.get_import_conduit(units, existing_units=existing_units)
        config = importer_mocks.get_basic_config()
        config.override_config['recursive'] = True
        config.override_config['resolve_dependencies'] = True
        importer = YumImporter()
        # Test
        result = importer.import_units(repoA, repoB, conduit, config, units)
        # Verify
        associated_units = [mock_call[0][0] for mock_call in conduit.associate_unit.call_args_list]
        self.assertEqual(len(associated_units), len(existing_units))
        for u in associated_units:
            self.assertTrue(u in existing_units + units)