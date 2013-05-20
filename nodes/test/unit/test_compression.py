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

import shutil
import gzip

from unittest import TestCase
from tempfile import mktemp, mkdtemp


from pulp_node.compression import *


class TestCompression(TestCase):

    def setUp(self):
        self.tmp_dir = mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_compression(self):
        # Setup
        block = 'A' * 1024
        path = mktemp(dir=self.tmp_dir)
        with open(path, 'w+') as fp:
            fp.write(block)
        # Test
        compressed_path = compress(path)
        # Verify
        self.assertFalse(compressed(path))
        self.assertTrue(compressed(compressed_path))
        self.assertEqual(path + FILE_SUFFIX, compressed_path)
        with gzip.open(compressed_path) as fp:
            block_in = fp.read()
        self.assertEqual(block, block_in)

    def test_decompression(self):
        # Setup
        block = 'A' * 1024
        path = mktemp(dir=self.tmp_dir) + FILE_SUFFIX
        with gzip.open(path, 'wb') as fp:
            fp.write(block)
        # Test
        decompressed_path = decompress(path)
        # Verify
        self.assertEqual(path.rstrip(FILE_SUFFIX), decompressed_path)
        with open(decompressed_path) as fp:
            block_in = fp.read()
        self.assertEqual(block, block_in)

    def test_round_trip(self):
        # Setup
        block = 'A' * 10240
        path = mktemp(dir=self.tmp_dir)
        with open(path, 'w+') as fp:
            fp.write(block)
            # Test
        compressed_path = compress(path)
        decompressed_path = decompress(compressed_path)
        # Verify
        self.assertEqual(path, decompressed_path)
        with open(decompressed_path) as fp:
            block_in = fp.read()
        self.assertEqual(block, block_in)