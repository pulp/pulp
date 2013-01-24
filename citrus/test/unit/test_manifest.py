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
import tempfile
import shutil

from unittest import TestCase

from pulp.citrus.manifest import Manifest


class TestManifest(TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_write(self):
        # Test
        manifest = Manifest()
        units = [{1:2, 3:4}]
        manifest.write(self.tmp_dir, units)
        # Verify
        path = os.path.join(self.tmp_dir, 'units.json.gz')
        self.assertTrue(os.path.exists(path))

    def test_read(self):
        # Test
        manifest = Manifest()
        units = [{1:2, 3:4}]
        manifest.write(self.tmp_dir, units)
        # Verify
        path = os.path.join(self.tmp_dir, 'units.json.gz')
        url = 'file://%s' % path
        units_in = manifest.read(url)