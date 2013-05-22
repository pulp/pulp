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
import tarfile

from unittest import TestCase
from nectar.downloaders.curl import HTTPSCurlDownloader
from nectar.config import DownloaderConfig

from pulp_node import constants
from pulp_node.distributors.http.publisher import HttpPublisher
from pulp_node.manifest import Manifest
from pulp_node.distributors.publisher import TGZ_SUFFIX


class TestHttp(TestCase):

    TMP_ROOT = '/tmp/pulp/nodes/publishing'

    RELATIVE_PATH = 'redhat/packages'

    UNITS = [
        'test_1.unit',
        'test_2.unit',
        'test_3.unit',
    ]

    NUM_TARED_FILES = 3
    TARED_FILE = '%d.rpm'

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
            if n == 0:  # making the 1st one a directory of files
                os.mkdir(path)
                for x in range(0, self.NUM_TARED_FILES):
                    _path = os.path.join(path, self.TARED_FILE % x)
                    with open(_path, 'w') as fp:
                        fp.write(str(x))
            else:
                with open(path, 'w') as fp:
                    fp.write(fn)
            unit = {
                'type_id': 'unit',
                'unit_key': {'n':n},
                'storage_path': path,
                'relative_path': relative_path
            }
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
        manifest = Manifest()
        url = 'file://' + manifest_path
        manifest.fetch(url, working_dir, downloader)
        manifest.fetch_units(url, downloader)
        units = manifest.get_units()
        n = 0
        for unit, ref in units:
            file_content = 'test_%d' % n
            _download = unit['_download']
            url = _download['url']
            expected_url = '/'.join(
                (base_url,
                 publish_dir[1:],
                 repo_id, unit['relative_path']))
            if n == 0:
                expected_url += TGZ_SUFFIX
                self.assertTrue(unit[constants.PUBLISHED_AS_TARBALL])
            else:
                self.assertFalse(unit.get(constants.PUBLISHED_AS_TARBALL, False))
            self.assertEqual(url, expected_url)
            path = url.split('//', 1)[1]
            if n == 0:
                self.assertTrue(os.path.isfile(path))
            else:
                self.assertTrue(os.path.islink(path))
            if n == 0:
                with tarfile.open(path) as tb:
                    files = sorted(tb.getnames())
                self.assertEqual(len(files), self.NUM_TARED_FILES + 1)
            else:
                with open(path, 'rb') as fp:
                    unit_content = fp.read()
                    self.assertEqual(unit_content, file_content)
            self.assertEqual(unit['unit_key']['n'], n)
            n += 1
