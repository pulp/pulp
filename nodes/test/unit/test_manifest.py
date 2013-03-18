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

from pulp.common.download.downloaders.curl import HTTPSCurlDownloader
from pulp.common.download.config import DownloaderConfig

from pulp_node.manifest import Manifest

Manifest.UNITS_PER_FILE = 2


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
                self.assertEqual(units_out[i][int(k)], v)

    def test_write(self):
        # Test
        manifest = Manifest()
        units = []
        for i in range(0, self.NUM_UNITS):
            units.append({i: i + 1})
        manifest.write(self.tmp_dir, units)
        # Verify
        path = os.path.join(self.tmp_dir, Manifest.FILE_NAME)
        self.assertTrue(os.path.exists(path))
        fp = gzip.open(path)
        s = fp.read()
        fp.close()
        manifest = json.loads(s)
        units_in = []
        for unit_file in manifest['unit_files']:
            path = os.path.join(self.tmp_dir, unit_file)
            fp = gzip.open(path)
            units_in.extend(json.load(fp))
            fp.close()
        self.assertEqual(manifest['total_units'], self.NUM_UNITS)
        self.verify(units, units_in)

    def test_round_trip(self):
        # Test
        manifest = Manifest()
        units = []
        for i in range(0, self.NUM_UNITS):
            units.append({i:i+1})
        manifest.write(self.tmp_dir, units)
        cfg = DownloaderConfig('http')
        downloader = HTTPSCurlDownloader(cfg)
        manifest = Manifest()
        path = os.path.join(self.tmp_dir, Manifest.FILE_NAME)
        url = 'file://%s' % path
        units_in = list(manifest.read(url, downloader))
        # Verify
        self.verify(units, units_in)
