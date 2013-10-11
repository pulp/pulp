# Copyright (c) 2013 Red Hat, Inc.
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
import json
import shutil
import time

from mock import patch
from unittest import TestCase
from tempfile import mkdtemp

from pulp_node import manifest as _manifest
from pulp_node.migration import *


MANIFEST_ID = 'test_1'

manifest_1 = {
    VERSION: 1,
    TOTAL_UNITS: 100,
    UNITS_SIZE: 123,
}

manifest_2 = {
    VERSION: 2,
    UNITS: {
        _manifest.UNITS_PATH: None,
        _manifest.UNITS_TOTAL: manifest_1[TOTAL_UNITS],
        _manifest.UNITS_SIZE: manifest_1[UNITS_SIZE]
    }
}


class TestManifestMigration(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.tmp_dir = mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_migration_1(self):
        manifest = migration_1(dict(manifest_1))
        self.assertFalse(TOTAL_UNITS in manifest)
        self.assertFalse(UNITS_SIZE in manifest)
        self.assertEqual(manifest[UNITS], manifest_2[UNITS])

    def test_migrate(self):
        path = os.path.join(self.tmp_dir, _manifest.MANIFEST_FILE_NAME)
        with open(path, 'w+') as fp:
            json.dump(manifest_1, fp)
        last_modified = os.path.getmtime(path)
        time.sleep(1)  # getmtime() is to the second.
        migrate(path)
        manifest = _manifest.Manifest(path, manifest_id=MANIFEST_ID)
        manifest.read()
        self.assertEqual(manifest.id, MANIFEST_ID)
        self.assertEqual(manifest.version, _manifest.MANIFEST_VERSION)
        self.assertEqual(manifest.units, manifest_2[UNITS])
        self.assertEqual(manifest.path, path)
        self.assertNotEqual(last_modified, os.path.getmtime(path))

    def test_migrate_unwritten(self):
        path = os.path.join(self.tmp_dir, _manifest.MANIFEST_FILE_NAME)
        with open(path, 'w+') as fp:
            json.dump(manifest_1, fp)
        migrate(path)
        manifest = _manifest.Manifest(path, manifest_id=MANIFEST_ID)
        manifest.read()
        self.assertEqual(manifest.id, MANIFEST_ID)
        self.assertEqual(manifest.version, _manifest.MANIFEST_VERSION)
        self.assertEqual(manifest.units, manifest_2[UNITS])
        self.assertEqual(manifest.path, path)
        last_modified = os.path.getmtime(path)
        time.sleep(1)  # getmtime() is to the second.
        migrate(path)
        self.assertEqual(last_modified, os.path.getmtime(path))

    @patch('pulp_node.migration.migration_1')
    def test_nothing_migrated(self, mocked_migration):
        path = os.path.join(self.tmp_dir, _manifest.MANIFEST_FILE_NAME)
        with open(path, 'w+') as fp:
            json.dump(manifest_2, fp)
        migrate(path)
        manifest = _manifest.Manifest(path, manifest_id=MANIFEST_ID)
        manifest.read()
        self.assertFalse(mocked_migration.called)
        self.assertEqual(manifest.id, MANIFEST_ID)
        self.assertEqual(manifest.version, _manifest.MANIFEST_VERSION)
        self.assertEqual(manifest.units, manifest_2[UNITS])
        self.assertEqual(manifest.path, path)