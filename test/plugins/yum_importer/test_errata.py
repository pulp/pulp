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
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../../../plugins/importers/yum_importer/")
import errata
import importer_mocks
from importer import YumImporter
from importer import YUM_IMPORTER_TYPE_ID
from pulp.server.content.plugins.model import Repository, Unit

class TestErrata(unittest.TestCase):

    def setUp(self):
        super(TestErrata, self).setUp()
        self.working_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "../data")
        self.repo_dir = os.path.abspath(os.path.dirname(__file__)) + "/../data/test_repo/"

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

