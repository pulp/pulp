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

import os
import sys
import mock
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../src/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../plugins/importers/")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../common")
import importer_mocks
import tempfile

from yum_importer import errata
from yum_importer import importer_rpm
from yum_importer.importer import YumImporter
from yum_importer.importer import YUM_IMPORTER_TYPE_ID
from pulp.plugins.model import Repository, Unit
from yum_importer.importer_rpm import RPM_TYPE_ID

class TestErrata(unittest.TestCase):

    def setUp(self):
        super(TestErrata, self).setUp()
        self.temp_dir = tempfile.mkdtemp()

        self.working_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
        self.repo_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data", "test_repo")
        self.data_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")

        self.pkg_dir = os.path.join(self.temp_dir, "packages")

    def tearDown(self):
        super(TestErrata, self).tearDown()

    def test_metadata(self):
        metadata = YumImporter.metadata()
        self.assertEquals(metadata["id"], YUM_IMPORTER_TYPE_ID)
        print metadata["types"]
        self.assertTrue(errata.ERRATA_TYPE_ID in metadata["types"])

    def test_errata_sync(self):
        feed_url = "http://example.com/test_repo/"
        importer = YumImporter()
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_repo"
        sync_conduit = importer_mocks.get_sync_conduit()
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        importer_errata = errata.ImporterErrata()
        status, summary, details = importer_errata.sync(repo, sync_conduit, config)
        self.assertTrue(status)
        self.assertTrue(summary is not None)
        self.assertTrue(details is not None)

        self.assertEquals(summary["num_new_errata"], 52)
        self.assertEquals(summary["num_existing_errata"], 0)
        self.assertEquals(summary["num_orphaned_errata"], 0)

        self.assertEquals(details["num_bugfix_errata"], 36)
        self.assertEquals(details["num_security_errata"], 7)
        self.assertEquals(details["num_enhancement_errata"], 9)

    def test_get_available_errata(self):
        errata_items_found = errata.get_available_errata(self.repo_dir)
        print len(errata_items_found)
        self.assertEqual(52, len(errata_items_found))

    def test_get_existing_errata(self):
        unit_key = dict()
        unit_key['id'] = "RHBA-2007:0112"
        metadata = {}
        existing_units = [Unit(errata.ERRATA_TYPE_ID, unit_key, metadata, '')]
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=existing_units)
        created_existing_units = errata.get_existing_errata(sync_conduit)
        self.assertEquals(len(created_existing_units), 1)
        self.assertEquals(len(existing_units), len(created_existing_units))

    def test_new_errata_units(self):
        # existing errata is newer or same as available errata; should skip sync for 1 errata
        available_errata = errata.get_available_errata(self.repo_dir)
        print len(available_errata)
        self.assertEqual(52, len(available_errata))
        unit_key = dict()
        unit_key['id'] = "RHBA-2007:0112"
        metadata = {}
        existing_units = [Unit(errata.ERRATA_TYPE_ID, unit_key, metadata, '')]
        existing_units[0].updated = "2007-03-14 00:00:00"
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=existing_units)
        created_existing_units = errata.get_existing_errata(sync_conduit)
        self.assertEquals(len(created_existing_units), 1)
        self.assertEquals(len(existing_units), len(created_existing_units))
        new_errata, new_units, sync_conduit = errata.get_new_errata_units(available_errata, created_existing_units, sync_conduit)
        print len(available_errata) - len(created_existing_units), len(new_errata)
        self.assertEquals(len(available_errata) - len(created_existing_units), len(new_errata))

    def test_update_errata_units(self):
        # existing errata is older than available; should purge and resync
        available_errata = errata.get_available_errata(self.repo_dir)
        print len(available_errata)
        self.assertEqual(52, len(available_errata))
        unit_key = dict()
        unit_key['id'] = "RHBA-2007:0112"
        metadata = {}
        existing_units = [Unit(errata.ERRATA_TYPE_ID, unit_key, metadata, '')]
        existing_units[0].updated = "2007-03-13 00:00:00"
        sync_conduit = importer_mocks.get_sync_conduit(existing_units=existing_units)
        created_existing_units = errata.get_existing_errata(sync_conduit)
        self.assertEquals(len(created_existing_units), 1)
        new_errata, new_units, sync_conduit = errata.get_new_errata_units(available_errata, created_existing_units, sync_conduit)
        self.assertEquals(len(available_errata), len(new_errata))

    def test_link_errata_rpm_units(self):
        feed_url = "file://%s/test_errata_local_sync/" % self.data_dir
        repo = mock.Mock(spec=Repository)
        repo.working_dir = self.working_dir
        repo.id = "test_errata_local_sync"
        repo.checksumtype = 'sha'
        sync_conduit = importer_mocks.get_sync_conduit(type_id=RPM_TYPE_ID, existing_units=[], pkg_dir=self.pkg_dir)
        config = importer_mocks.get_basic_config(feed_url=feed_url)
        importerRPM = importer_rpm.ImporterRPM()
        status, summary, details = importerRPM.sync(repo, sync_conduit, config)
        metadata = {}
        unit_key_a = {'id' : '','name' :'patb', 'version' :'0.1', 'release' : '2', 'epoch':'0', 'arch' : 'noarch', 'checksumtype' : 'sha',
                      'checksum': '017c12050a97cf6095892498750c2a39d2bf535e'}
        unit_key_b = {'id' : '', 'name' :'emoticons', 'version' :'0.1', 'release' :'2', 'epoch':'0','arch' : 'noarch', 'checksumtype' :'sha',
                      'checksum' : '663c89b0d29bfd5479d8736b716d50eed9495dbb'}

        existing_units = []
        for unit in [unit_key_a, unit_key_b]:
            existing_units.append(Unit(importer_rpm.ImporterRPM, unit, metadata, ''))
        sync_conduit = importer_mocks.get_sync_conduit(type_id=RPM_TYPE_ID, existing_units=existing_units, pkg_dir=self.pkg_dir)
        importerErrata = errata.ImporterErrata()
        status, summary, details = importerErrata.sync(repo, sync_conduit, config)
        self.assertEquals(len(details['link_report']['linked_units']), 2)
