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
import tempfile
import shutil
import gzip
import json

from unittest import TestCase

from nectar.downloaders.curl import HTTPSCurlDownloader
from nectar.config import DownloaderConfig

from pulp_node.manifest import *


class TestManifest(TestCase):

    NUM_UNITS = 10
    MANIFEST_ID = '123'

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def verify(self, units_out, units_in):
        self.assertEqual(len(units_out), self.NUM_UNITS)
        self.assertEqual(len(units_in), self.NUM_UNITS)
        for i in range(0, len(units_out)):
            for k, v in units_in[i].items():
                self.assertEqual(units_out[i][k], v)

    def test_validation(self):
        # Setup
        manifest_path = os.path.join(self.tmp_dir, MANIFEST_FILE_NAME)
        manifest = Manifest(manifest_path, self.MANIFEST_ID)
        # Test valid
        self.assertTrue(manifest.is_valid())
        # Test version mismatch
        manifest.version += 1
        self.assertFalse(manifest.is_valid())

    def test_publishing(self):
        # Setup
        units = []
        manifest_path = os.path.join(self.tmp_dir, MANIFEST_FILE_NAME)
        for i in range(0, self.NUM_UNITS):
            unit = dict(unit_id=i, type_id='T', unit_key={})
            units.append(unit)
        # Test
        units_path = os.path.join(self.tmp_dir, UNITS_FILE_NAME)
        writer = UnitWriter(units_path)
        for u in units:
            writer.add(u)
        writer.close()
        manifest = Manifest(manifest_path, self.MANIFEST_ID)
        manifest.units_published(writer)
        manifest.write()
        # Verify
        self.assertTrue(os.path.exists(manifest_path))
        with open(manifest_path) as fp:
            manifest_in = json.load(fp)
        self.assertEqual(manifest.id, manifest_in['id'])
        self.assertEqual(manifest.units[UNITS_TOTAL], manifest_in['units'][UNITS_TOTAL])
        self.assertEqual(manifest.units[UNITS_TOTAL], writer.total_units)
        self.assertEqual(manifest.units[UNITS_TOTAL], len(units))
        self.assertTrue(os.path.exists(manifest_path))
        self.assertTrue(os.path.exists(units_path))
        units_in = []
        fp = gzip.open(units_path)
        while True:
            json_unit = fp.readline()
            if json_unit:
                units_in.append(json.loads(json_unit))
            else:
                break
        fp.close()
        self.verify(units, units_in)

    def test_round_trip(self):
        # Setup
        units = []
        manifest_path = os.path.join(self.tmp_dir, MANIFEST_FILE_NAME)
        for i in range(0, self.NUM_UNITS):
            unit = dict(unit_id=i, type_id='T', unit_key={})
            units.append(unit)
        units_path = os.path.join(self.tmp_dir, UNITS_FILE_NAME)
        writer = UnitWriter(units_path)
        for u in units:
            writer.add(u)
        writer.close()
        manifest = Manifest(manifest_path, self.MANIFEST_ID)
        manifest.units_published(writer)
        manifest.write()
        # Test
        cfg = DownloaderConfig()
        downloader = HTTPSCurlDownloader(cfg)
        working_dir = os.path.join(self.tmp_dir, 'working_dir')
        os.makedirs(working_dir)
        path = os.path.join(self.tmp_dir, MANIFEST_FILE_NAME)
        url = 'file://%s' % path
        manifest = RemoteManifest(url, downloader, working_dir)
        manifest.fetch()
        manifest.fetch_units()
        # Verify
        self.assertTrue(manifest.is_valid())
        self.assertTrue(manifest.has_valid_units())
        units_in = []
        for unit, ref in manifest.get_units():
            units_in.append(unit)
            _unit = ref.fetch()
            self.assertEqual(unit, _unit)
        self.verify(units, units_in)
        # should already be unzipped
        self.assertTrue(manifest.is_valid())
        self.assertTrue(manifest.has_valid_units())
        self.assertFalse(manifest.units_path().endswith('.gz'))
        units_in = []
        for unit, ref in manifest.get_units():
            units_in.append(unit)
            _unit = ref.fetch()
            self.assertEqual(unit, _unit)
        self.verify(units, units_in)