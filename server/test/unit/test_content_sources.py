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

from uuid import uuid4
from tempfile import mkdtemp
from mock import patch, Mock
from unittest import TestCase

from nectar.config import DownloaderConfig
from nectar.downloaders.local import LocalFileDownloader

from base import PulpAsyncServerTests

from pulp.plugins.conduits.cataloger import CatalogerConduit
from pulp.server.db.model.content import ContentCatalog
from pulp.server.content.sources import Coordinator, Request, ContentSource, Listener
from pulp.server.content.sources.descriptor import to_seconds, is_valid
from pulp.server.managers import factory as managers


PRIMARY = 'primary'
UNIT_WORLD = 'unit-world'
UNDERGROUND = 'underground-content'
ORPHANED = 'orphaned'

TYPE_ID = 'rpm'
EXPIRES = 600


ALT_1 = """
[%s]
enabled: 1
type: yum
name: Unit World
priority: 1
max_concurrent: 10
base_url: file:///unit-world/
""" % UNIT_WORLD

ALT_2 = """
[%s]
enabled: 1
type: yum
name: Underground Content
priority: 2
base_url: file:///underground
paths: fedora/18/x86_64 \
       fedora/18/i386   \
       fedora/19/x86_64 \
       fedora/19/i386 \
       \\
""" % UNDERGROUND

DISABLED = """
[disabled]
enabled: 0
type: yum
name: Test Not Enabled
priority: 2
base_url: http:///disabled.com/
"""

MISSING_ENABLED = """
[missing-enabled]
type: yum
name: Test Invalid
priority: 2
base_url: http:///invalid/
"""

MISSING_TYPE = """
[missing-type]
enabled: 1
name: Test Invalid
priority: 2
base_url: http:///invalid/
"""

MISSING_BASE_URL = """
[missing-base_url]
enabled: 1
type: yum
name: Test Invalid
priority: 2
"""


class MockCataloger(object):

    refresh = Mock()


class MockListener(Listener):

    download_started = Mock()
    download_succeeded = Mock()
    download_failed = Mock()


class ContentTest(PulpAsyncServerTests):

    def setUp(self):
        PulpAsyncServerTests.setUp(self)
        ContentCatalog.get_collection().remove()
        self.tmp_dir = mkdtemp()
        self.downloaded = os.path.join(self.tmp_dir, 'downloaded')
        os.makedirs(self.downloaded)
        self.add_sources()
        MockListener.download_started.reset_mock()
        MockListener.download_succeeded.reset_mock()
        MockListener.download_failed.reset_mock()

    def tearDown(self):
        PulpAsyncServerTests.tearDown(self)
        ContentCatalog.get_collection().remove()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def add_sources(self):
        # unit-world
        path = os.path.join(self.tmp_dir, 'unit-world.conf')
        with open(path, 'w+') as fp:
            fp.write(ALT_1)
        # underground-content
        path = os.path.join(self.tmp_dir, 'underground-content.conf')
        with open(path, 'w+') as fp:
            fp.write(ALT_2)
        # other
        path = os.path.join(self.tmp_dir, 'other.conf')
        with open(path, 'w+') as fp:
            for descriptor in (DISABLED, MISSING_ENABLED, MISSING_TYPE, MISSING_BASE_URL):
                fp.write(descriptor)

    def populate_content(self, source, n_start, n_units):
        _dir = os.path.join(self.tmp_dir, source)
        os.makedirs(_dir)
        for n in range(n_start, n_start + n_units):
            path = os.path.join(_dir, 'unit_%d' % n)
            with open(path, 'w+') as fp:
                fp.write(path)
        return _dir

    def populate_catalog(self, source_id, n_start, n_units, checksum='0xAA'):
        _dir = self.populate_content(source_id, n_start, n_units)
        collection = ContentCatalog.get_collection()
        entry_list = []
        for n in range(n_start, n_start + n_units):
            unit_key = {
                'name': 'unit_%d' % n,
                'version': '1.0.%d' % n,
                'release': '1',
                'checksum': checksum
            }
            url = 'file://%s/unit_%d' % (_dir, n)
            entry = ContentCatalog(source_id, EXPIRES, TYPE_ID, unit_key, url)
            entry_list.append(entry)
        for entry in entry_list:
            collection.insert(entry, safe=True)
        return _dir, entry_list


class TestLoading(ContentTest):

    def test_loading(self):
        sources = ContentSource.load_all(self.tmp_dir)
        self.assertEqual(len(sources), 2)

    def test_urls(self):
        sources = ContentSource.load_all(self.tmp_dir)
        underground = sources[UNDERGROUND]
        urls = underground.urls()
        self.assertEqual(len(urls), 4)
        self.assertEqual(urls[0], 'file:///underground/fedora/18/x86_64/')
        self.assertEqual(urls[1], 'file:///underground/fedora/18/i386/')
        self.assertEqual(urls[2], 'file:///underground/fedora/19/x86_64/')
        self.assertEqual(urls[3], 'file:///underground/fedora/19/i386/')


class TestDownloading(ContentTest):

    def test_download(self):
        request_list = []
        _dir, cataloged = self.populate_catalog(ORPHANED, 0, 10)
        _dir, cataloged = self.populate_catalog(UNIT_WORLD, 0, 10)
        _dir = self.populate_content(PRIMARY, 0, 20)
        # unit-world
        for n in range(0, 10):
            request = Request(
                cataloged[n].type_id,
                cataloged[n].unit_key,
                'file://%s/unit_%d' % (_dir, n),
                os.path.join(self.downloaded, 'unit_%d' % n))
            request_list.append(request)
        # primary
        for n in range(11, 20):
            unit_key = {
                'name': 'unit_%d' % n,
                'version': '1.0.%d' % n,
                'release': '1',
                'checksum': str(uuid4())
            }
            request = Request(
                TYPE_ID,
                unit_key,
                'file://%s/unit_%d' % (_dir, n),
                os.path.join(self.downloaded, 'unit_%d' % n))
            request_list.append(request)
        downloader = LocalFileDownloader(DownloaderConfig())
        listener = MockListener()
        coordinator = Coordinator(path=self.tmp_dir, listener=listener)
        coordinator.refresh = Mock()
        coordinator.download(downloader, request_list)
        # unit-world
        for i in range(0, 10):
            request = request_list[i]
            self.assertTrue(request.downloaded)
            self.assertEqual(len(request.errors), 0)
            with open(request.destination) as fp:
                s = fp.read()
                self.assertTrue(UNIT_WORLD in s)
        # primary
        for i in range(11, len(request_list)):
            request = request_list[i]
            self.assertTrue(request.downloaded)
            self.assertEqual(len(request.errors), 0)
            with open(request.destination) as fp:
                s = fp.read()
                self.assertTrue(PRIMARY in s)
        self.assertEqual(listener.download_started.call_count, len(request_list))
        self.assertEqual(listener.download_succeeded.call_count, len(request_list))
        self.assertEqual(listener.download_failed.call_count, 0)

    def test_download_with_errors(self):
        request_list = []
        _dir, cataloged = self.populate_catalog(ORPHANED, 0, 10)
        _dir, cataloged = self.populate_catalog(UNDERGROUND, 0, 10)
        _dir, cataloged = self.populate_catalog(UNIT_WORLD, 0, 10)
        shutil.rmtree(_dir)
        _dir = self.populate_content(PRIMARY, 0, 20)
        # unit-world
        for n in range(0, 10):
            request = Request(
                cataloged[n].type_id,
                cataloged[n].unit_key,
                'file://%s/unit_%d' % (_dir, n),
                os.path.join(self.downloaded, 'unit_%d' % n))
            request_list.append(request)
        # primary
        for n in range(11, 20):
            unit_key = {
                'name': 'unit_%d' % n,
                'version': '1.0.%d' % n,
                'release': '1',
                'checksum': str(uuid4())
            }
            request = Request(
                TYPE_ID,
                unit_key,
                'file://%s/unit_%d' % (_dir, n),
                os.path.join(self.downloaded, 'unit_%d' % n))
            request_list.append(request)
        downloader = LocalFileDownloader(DownloaderConfig())
        listener = MockListener()
        coordinator = Coordinator(path=self.tmp_dir, listener=listener)
        coordinator.refresh = Mock()
        coordinator.download(downloader, request_list)
        # unit-world
        for i in range(0, 10):
            request = request_list[i]
            self.assertTrue(request.downloaded)
            self.assertEqual(len(request.errors), 1)
            with open(request.destination) as fp:
                s = fp.read()
                self.assertTrue(UNDERGROUND in s)
        # primary
        for i in range(11, len(request_list)):
            request = request_list[i]
            self.assertTrue(request.downloaded)
            self.assertEqual(len(request.errors), 0)
            with open(request.destination) as fp:
                s = fp.read()
                self.assertTrue(PRIMARY in s)
        self.assertEqual(listener.download_started.call_count, len(request_list))
        self.assertEqual(listener.download_succeeded.call_count, len(request_list))
        self.assertEqual(listener.download_failed.call_count, 0)


class TestRefreshing(ContentTest):

    @patch('pulp.plugins.loader.api.get_cataloger_by_id', return_value=(MockCataloger(), {}))
    def test_refresh(self, mock):
        coordinator = Coordinator(path=self.tmp_dir)
        coordinator.refresh(force=True)
        plugin = mock.return_value[0]
        self.assertEqual(plugin.refresh.call_count, 5)
        calls = iter(plugin.refresh.call_args_list)
        for source in ContentSource.load_all(self.tmp_dir).values():
            for url in source.urls():
                args = calls.next()[0]
                self.assertTrue(isinstance(args[0], CatalogerConduit))
                self.assertEqual(args[1], source.descriptor)
                self.assertEqual(args[2], url)

    def test_purge_orphans(self):
        _dir, cataloged = self.populate_catalog(ORPHANED, 0, 10)
        _dir, cataloged = self.populate_catalog(UNDERGROUND, 0, 10)
        _dir, cataloged = self.populate_catalog(UNIT_WORLD, 0, 10)
        collection = ContentCatalog.get_collection()
        self.assertEqual(collection.find().count(), 30)
        coordinator = Coordinator(path=self.tmp_dir)
        coordinator.purge_orphans()
        self.assertEqual(collection.find().count(), 20)
        self.assertEqual(collection.find({'source_id': ORPHANED}).count(), 0)
        self.assertEqual(collection.find({'source_id': UNDERGROUND}).count(), 10)
        self.assertEqual(collection.find({'source_id': UNIT_WORLD}).count(), 10)


class TestDescriptor(TestCase):

    def setUp(self):
        self.tmp_dir = mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_to_seconds(self):
        self.assertEqual(to_seconds('10'), 10)
        self.assertEqual(to_seconds('10s'), 10)
        self.assertEqual(to_seconds('10m'), 600)
        self.assertEqual(to_seconds('10h'), 36000)
        self.assertEqual(to_seconds('10d'), 864000)

    @patch('pulp.server.content.sources.model.ContentSource.is_valid', return_value=True)
    @patch('pulp.server.content.sources.model.ContentSource.enabled', return_value=True)
    def test_invalid(self, *unused):
        path = os.path.join(self.tmp_dir, 'other.conf')
        with open(path, 'w+') as fp:
            for other in (MISSING_ENABLED, MISSING_TYPE, MISSING_BASE_URL):
                fp.write(other)
        sources = ContentSource.load_all(self.tmp_dir)
        for source_id, source in sources.items():
            self.assertFalse(is_valid(source_id, source.descriptor))
