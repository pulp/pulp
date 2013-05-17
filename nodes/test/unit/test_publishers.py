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
import shutil
import tempfile

from unittest import TestCase
from nectar.downloaders.curl import HTTPSCurlDownloader
from nectar.config import DownloaderConfig
from pulp_node.distributors.http.publisher import HttpPublisher
from pulp_node.manifest import ManifestReader


class TestHttp(TestCase):

    TMP_ROOT = '/tmp/pulp/nodes/publishing'

    RELATIVE_PATH = 'redhat/packages'

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
        os.makedirs(os.path.join(self.unit_dir, self.RELATIVE_PATH))

    def shutDown(self):
        shutil.rmtree(self.TMP_ROOT)

    def test_publisher(self):
        # setup
        units = []
        for n in range(0, 3):
            fn = 'test_%d' % n
            relative_path = os.path.join(self.RELATIVE_PATH, fn)
            path = os.path.join(self.unit_dir, relative_path)
            fp = open(path, 'w')
            fp.write(fn)
            fp.close()
            unit = {'type_id':'unit', 'unit_key':{'n':n}, 'storage_path':path, 'relative_path':relative_path}
            units.append(unit)
        # test
        # publish
        repo_id = 'test_repo'
        base_url = 'file://'
        publish_dir = os.path.join(self.tmpdir, 'nodes/repos')
        virtual_host = (publish_dir, publish_dir)
        p = HttpPublisher(base_url, virtual_host, repo_id)
        p.publish(units)
        # verify
        conf = DownloaderConfig()
        downloader = HTTPSCurlDownloader(conf)
        manifest_path = p.manifest_path()
        working_dir = os.path.join(self.tmpdir, 'working_dir')
        os.makedirs(working_dir)
        manifest_reader = ManifestReader(downloader, working_dir)
        url = 'file://' + manifest_path
        manifest = manifest_reader.read(url)
        units = manifest.get_units()
        n = 0
        for unit, ref in units:
            file_content = 'test_%d' % n
            _download = unit['_download']
            url = _download['url']
            self.assertEqual(url, '/'.join((base_url, publish_dir[1:], repo_id, unit['relative_path'])))
            path = url.split('//', 1)[1]
            self.assertTrue(os.path.islink(path))
            f = open(path)
            s = f.read()
            f.close()
            self.assertEqual(s, file_content)
            self.assertEqual(unit['unit_key']['n'], n)
            n += 1
