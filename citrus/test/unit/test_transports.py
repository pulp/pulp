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
import tempfile

from unittest import TestCase
from pulp.citrus.transport import HttpPublisher, HttpReader

class TestHttp(TestCase):

    TMP_ROOT = '/tmp/pulp/citrus/transport'

    UNITS = [
        'test_1.unit',
        'test_2.unit',
        'test_3.unit',
    ]

    def setUp(self):
        if not os.path.exists(self.TMP_ROOT):
            os.makedirs(self.TMP_ROOT)
        self.tmpdir = tempfile.mkdtemp(dir=self.TMP_ROOT)
        self.unit_dir = os.path.join(self.tmpdir, 'unit_storage')
        shutil.rmtree(self.tmpdir)
        os.makedirs(self.unit_dir)

    def shutDown(self):
        shutil.rmtree(self.TMP_ROOT)

    def test_http(self):
        # setup
        units = []
        for i in range(0, 3):
            fn = 'test_%d.unit' % i
            path = os.path.join(self.unit_dir, fn)
            fp = open(path, 'w')
            fp.write(fn)
            fp.close()
            unit = {'type_id':'unit', 'storage_path':path}
            units.append(unit)
        # test
        # publish
        repo_id = 'elmer'
        publish_dir = os.path.join(self.tmpdir, 'citrus/repos')
        base_url = '/'.join(('file://', publish_dir))
        reader = HttpReader(base_url)
        p = HttpPublisher(publish_dir, repo_id)
        p.publish(units)
        # read
        fp = reader.open(repo_id, 'units.json')
        s = fp.read()
        print s
        fp.close()
        publish_dir = os.path.join(self.tmpdir, 'citrus', 'repos', repo_id, 'content')
        for fn in os.listdir(publish_dir):
            path = os.path.join(self.tmpdir, fn)
            fp = reader.open(repo_id, 'content', fn)
            s = fp.read()
            print s
            fp.close()