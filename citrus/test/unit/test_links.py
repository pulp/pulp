# Copyright (c) 2012 Red Hat, Inc.
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
import shutil

from base64 import b64encode
from tempfile import mkdtemp
from unittest import TestCase

from pulp_citrus import link

CONTENT = 'hello'

class TestLinks(TestCase):

    def setUp(self):
        self.tmp_dir = mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_pack(self):
        # Setup
        path = os.path.join(self.tmp_dir, 'A')
        fp = open(path, 'w')
        fp.write(CONTENT)
        fp.close()
        # Test
        path_out = os.path.join(self.tmp_dir, 'B')
        packed = link.pack(path, path_out)
        # Verify
        self.assertTrue(isinstance(packed, dict))
        self.assertTrue(link.SIGNATURE in packed)
        self.assertEqual(packed[link.SIGNATURE]['path'], path_out)
        self.assertEqual(packed[link.SIGNATURE]['content'], b64encode(CONTENT))

    def test_shallow(self):
        # Setup
        path = os.path.join(self.tmp_dir, 'A')
        fp = open(path, 'w')
        fp.write(CONTENT)
        fp.close()
        # Test
        path_out = os.path.join(self.tmp_dir, 'B')
        packed = link.pack(path, path_out)
        d = {'elmer':packed}
        self.assertTrue(link.is_link(d['elmer']))
        unpacked = link.unpack_all(d)
        self.assertEqual(unpacked['elmer'], path_out)
        f = open(path_out)
        s = f.read()
        f.close()
        self.assertEqual(s, CONTENT)

    def test_dict(self):
        # Setup
        path = os.path.join(self.tmp_dir, 'A')
        fp = open(path, 'w')
        fp.write(CONTENT)
        fp.close()
        # Test
        path_out = os.path.join(self.tmp_dir, 'B')
        packed = link.pack(path, path_out)
        d = {'name': {'elmer':packed}, 'age': 30}
        self.assertTrue(link.is_link(d['name']['elmer']))
        unpacked = link.unpack_all(d)
        self.assertEqual(unpacked['name']['elmer'], path_out)
        self.assertEqual(unpacked['age'], 30)
        f = open(path_out)
        s = f.read()
        f.close()
        self.assertEqual(s, CONTENT)

    def test_list(self):
        # Setup
        path = os.path.join(self.tmp_dir, 'A')
        fp = open(path, 'w')
        fp.write(CONTENT)
        fp.close()
        # Test
        path_out = os.path.join(self.tmp_dir, 'B')
        packed = link.pack(path, path_out)
        lst = [
            {'elmer':packed},
            packed,
            10,
            'stones'
        ]
        self.assertTrue(link.is_link(lst[0]['elmer']))
        self.assertTrue(link.is_link(lst[1]))
        unpacked = link.unpack_all(lst)
        self.assertEqual(unpacked[0]['elmer'], path_out)
        self.assertEqual(unpacked[1], path_out)
        self.assertEqual(unpacked[2], 10)
        self.assertEqual(unpacked[3], 'stones')
        f = open(path_out)
        s = f.read()
        f.close()
        self.assertEqual(s, CONTENT)

