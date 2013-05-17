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

from pulp_node import manifest
from pulp_node.manifest import ManifestWriter, ManifestReader


class TestManifest(TestCase):

    NUM_UNITS = 10

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

    def test_writer(self):
        # Test
        writer = ManifestWriter(self.tmp_dir)
        units = []
        for i in range(0, self.NUM_UNITS):
            unit = dict(unit_id=i, type_id='T', unit_key={})
            units.append(unit)
        writer.open()
        for u in units:
            writer.add_unit(u)
        writer.close()
        # Verify
        path = os.path.join(self.tmp_dir, manifest.MANIFEST_FILE_NAME)
        self.assertTrue(os.path.exists(path))
        fp = gzip.open(path)
        s = fp.read()
        manifest_in = json.loads(s)
        fp.close()
        units_in = []
        path = os.path.join(self.tmp_dir, manifest_in[manifest.UNIT_FILE])
        fp = gzip.open(path)
        while True:
            json_unit = fp.readline()
            if json_unit:
                units_in.append(json.loads(json_unit))
            else:
                break
        fp.close()
        self.verify(units, units_in)

    def test_round_trip(self):
        # Test
        writer = ManifestWriter(self.tmp_dir)
        units = []
        for i in range(0, self.NUM_UNITS):
            unit = dict(unit_id=i, type_id='T', unit_key={})
            units.append(unit)
        writer.open()
        for u in units:
            writer.add_unit(u)
        writer.close()
        cfg = DownloaderConfig()
        downloader = HTTPSCurlDownloader(cfg)
        working_dir = os.path.join(self.tmp_dir, 'working_dir')
        os.makedirs(working_dir)
        reader = ManifestReader(downloader, working_dir)
        path = os.path.join(self.tmp_dir, manifest.MANIFEST_FILE_NAME)
        url = 'file://%s' % path
        manifest_in = reader.read(url)
        # Verify
        units_in = []
        for unit, ref in manifest_in.get_units():
            units_in.append(unit)
            _unit = ref.fetch()
            self.assertEqual(unit, _unit)
        self.verify(units, units_in)
