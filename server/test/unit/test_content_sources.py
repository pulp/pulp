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
from threading import Event

from nectar.config import DownloaderConfig
from nectar.downloaders.local import LocalFileDownloader
from nectar.downloaders.threaded import HTTPThreadedDownloader

from base import PulpAsyncServerTests

from pulp.plugins.loader import api as plugins
from pulp.plugins.conduits.cataloger import CatalogerConduit
from pulp.server.db.model.content import ContentCatalog
from pulp.server.content.sources import ContentContainer, Request, ContentSource, Listener
from pulp.server.content.sources.descriptor import to_seconds, is_valid
from pulp.server.content.sources import model
from pulp.server.content.sources.container import NectarListener


PRIMARY = 'primary'
UNIT_WORLD = 'unit-world'
UNIT_WORLD_SECURE = 'unit-world-secure'
UNDERGROUND = 'underground-content'
ORPHANED = 'orphaned'
UNSUPPORTED_PROTOCOL = 'unsupported-protocol'

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

ALT_3 = """
[%s]
enabled: 1
type: yum
name: Unit World
priority: 1
max_concurrent: 10
base_url: ftp:///unit-world/
""" % UNSUPPORTED_PROTOCOL

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

MOST_SECURE = """
[%s]
enabled: 0
type: yum
name: Secure Unit World
priority: 1
max_concurrent: 10
base_url: https:///unit-world/units
max_concurrent: 10
max_speed: 1000
ssl_ca_cert: /my-ca
ssl_validation: true
ssl_client_cert: /my-client-cert
ssl_client_key: /my-client-key
proxy_url: /my-proxy-url
proxy_port: 9090
proxy_username: proxy-user
proxy_password: proxy-password
""" % UNIT_WORLD_SECURE

OTHER_SOURCES = (DISABLED, MISSING_ENABLED, MISSING_TYPE, MISSING_BASE_URL, MOST_SECURE)


class MockCataloger(object):

    def __init__(self, exception=None):
        self.exception = exception
        self.refresh = Mock(side_effect=self._refresh)

    def _refresh(self, conduit, *unused):
        conduit.added_count = 100
        if self.exception:
            raise self.exception


class MockListener(Listener):

    download_started = Mock()
    download_succeeded = Mock()
    download_failed = Mock()


class CancelEvent(object):

    def __init__(self, on_call):
        self.on_call = on_call
        self.call_count = 0

    def isSet(self):
        self.call_count += 1
        return self.call_count >= self.on_call


class ContainerTest(PulpAsyncServerTests):

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
        plugins._create_manager()
        plugins._MANAGER.catalogers.add_plugin('yum', MockCataloger, {})

    def tearDown(self):
        PulpAsyncServerTests.tearDown(self)
        ContentCatalog.get_collection().remove()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        plugins.finalize()

    def add_sources(self):
        # unit-world
        path = os.path.join(self.tmp_dir, '%s.conf' % UNIT_WORLD)
        with open(path, 'w+') as fp:
            fp.write(ALT_1)
        # underground-content
        path = os.path.join(self.tmp_dir, '%s.conf' % UNDERGROUND)
        with open(path, 'w+') as fp:
            fp.write(ALT_2)
        # unsupported protocol
        path = os.path.join(self.tmp_dir, '%s.conf' % UNSUPPORTED_PROTOCOL)
        with open(path, 'w+') as fp:
            fp.write(ALT_3)
        # other
        path = os.path.join(self.tmp_dir, 'other.conf')
        with open(path, 'w+') as fp:
            for descriptor in OTHER_SOURCES:
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


class TestLoading(ContainerTest):

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

    @patch('pulp.server.content.sources.model.ContentSource.enabled', return_value=True)
    def test_nectar_config(self, *unused):
        sources = ContentSource.load_all(self.tmp_dir)
        unit_world = sources[UNIT_WORLD_SECURE]
        downloader = unit_world.downloader()
        self.assertEqual(downloader.config.max_concurrent, 10)
        self.assertEqual(downloader.config.max_speed, 1000)
        self.assertEqual(downloader.config.ssl_validation, True)
        self.assertEqual(downloader.config.ssl_client_cert, '/my-client-cert')
        self.assertEqual(downloader.config.ssl_client_key, '/my-client-key')
        self.assertEqual(downloader.config.proxy_url, '/my-proxy-url')
        self.assertEqual(downloader.config.proxy_port, 9090)
        self.assertEqual(downloader.config.proxy_username, 'proxy-user')
        self.assertEqual(downloader.config.proxy_password, 'proxy-password')


class TestDownloading(ContainerTest):

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
        container = ContentContainer(path=self.tmp_dir)
        container.refresh = Mock()
        event = Event()
        container.download(event, downloader, request_list, listener)
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

    def test_download_cancelled_during_refreshing(self):
        downloader = LocalFileDownloader(DownloaderConfig())
        container = ContentContainer(path=self.tmp_dir)
        container.collated = Mock()
        event = CancelEvent(1)
        container.download(event, downloader, [])
        self.assertFalse(container.collated.called)

    def test_download_cancelled_in_download(self):
        container = ContentContainer(path=self.tmp_dir)
        container.collated = Mock()
        event = CancelEvent(1)
        container.download(event, None, [])
        self.assertFalse(container.collated.called)

    @patch('nectar.downloaders.base.Downloader.cancel')
    def test_download_cancelled_in_started(self, mock_cancel):
        request_list = []
        _dir = self.populate_content(PRIMARY, 0, 5)
        for n in range(0, 5):
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
        container = ContentContainer(path=self.tmp_dir)
        container.refresh = Mock()
        event = CancelEvent(2)
        container.download(event, downloader, request_list)
        self.assertTrue(mock_cancel.called)

    @patch('nectar.downloaders.base.Downloader.cancel')
    @patch('pulp.server.content.sources.container.NectarListener.download_started')
    def test_download_cancelled_in_succeeded(self, mock_started, mock_cancel):
        request_list = []
        _dir = self.populate_content(PRIMARY, 0, 5)
        for n in range(0, 5):
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
        container = ContentContainer(path=self.tmp_dir)
        container.refresh = Mock()
        event = CancelEvent(2)
        container.download(event, downloader, request_list)
        self.assertTrue(mock_started.called)
        self.assertTrue(mock_cancel.called)

    @patch('nectar.downloaders.base.Downloader.cancel')
    @patch('pulp.server.content.sources.container.NectarListener.download_started')
    def test_download_cancelled_in_failed(self, mock_started, mock_cancel):
        request_list = []
        for n in range(0, 5):
            unit_key = {
                'name': 'unit_%d' % n,
                'version': '1.0.%d' % n,
                'release': '1',
                'checksum': str(uuid4())
            }
            request = Request(
                TYPE_ID,
                unit_key,
                'http://unit-city/unit_%d' % n,
                os.path.join(self.downloaded, 'unit_%d' % n))
            request_list.append(request)
        downloader = HTTPThreadedDownloader(DownloaderConfig())
        container = ContentContainer(path=self.tmp_dir)
        container.refresh = Mock()
        event = CancelEvent(2)
        container.download(event, downloader, request_list)
        self.assertTrue(mock_started.called)
        self.assertTrue(mock_cancel.called)

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
        container = ContentContainer(path=self.tmp_dir)
        container.refresh = Mock()
        event = Event()
        container.download(event, downloader, request_list, listener)
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

    def test_download_fail_completely(self):
        request_list = []
        _dir, cataloged = self.populate_catalog(UNIT_WORLD, 0, 10)
        shutil.rmtree(_dir)
        _dir = self.populate_content(PRIMARY, 0, 20)
        # primary
        for n in range(0, 10):
            unit_key = {
                'name': 'unit_%d' % n,
                'version': '1.0.%d' % n,
                'release': '1',
                'checksum': str(uuid4())
            }
            request = Request(
                TYPE_ID,
                unit_key,
                'http://redhat.com/%s/unit_%d' % (_dir, n),
                os.path.join(self.downloaded, 'unit_%d' % n))
            request_list.append(request)
        downloader = HTTPThreadedDownloader(DownloaderConfig())
        listener = MockListener()
        container = ContentContainer(path=self.tmp_dir)
        container.refresh = Mock()
        event = Event()
        container.download(event, downloader, request_list, listener)
        # primary
        for i in range(0, len(request_list)):
            request = request_list[i]
            self.assertFalse(request.downloaded)
            self.assertEqual(len(request.errors), 1)
        self.assertEqual(listener.download_started.call_count, len(request_list))
        self.assertEqual(listener.download_succeeded.call_count, 0)
        self.assertEqual(listener.download_failed.call_count, len(request_list))

    def test_download_with_unsupported_url(self):
        request_list = []
        _dir, cataloged = self.populate_catalog(UNSUPPORTED_PROTOCOL, 0, 10)
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
        container = ContentContainer(path=self.tmp_dir)
        container.refresh = Mock()
        event = Event()
        container.download(event, downloader, request_list, listener)
        for i in range(0, len(request_list)):
            request = request_list[i]
            self.assertTrue(request.downloaded)
            self.assertEqual(len(request.errors), 0)
            with open(request.destination) as fp:
                s = fp.read()
                self.assertTrue(PRIMARY in s)
        self.assertEqual(listener.download_started.call_count, len(request_list))
        self.assertEqual(listener.download_succeeded.call_count, len(request_list))
        self.assertEqual(listener.download_failed.call_count, 0)


class TestRefreshing(ContainerTest):

    @patch('pulp.plugins.loader.api.get_cataloger_by_id', return_value=(MockCataloger(), {}))
    def test_refresh(self, mock_plugin):
        container = ContentContainer(path=self.tmp_dir)
        event = Event()
        report = container.refresh(event, force=True)
        plugin = mock_plugin.return_value[0]
        self.assertEqual(plugin.refresh.call_count, 5)
        self.assertEqual(len(report), 5)
        for r in report:
            self.assertTrue(r.succeeded)
            self.assertEqual(r.added_count, 100)
            self.assertEqual(r.deleted_count, 0)
        calls = iter(plugin.refresh.call_args_list)
        for source in ContentSource.load_all(self.tmp_dir).values():
            for url in source.urls():
                args = calls.next()[0]
                self.assertTrue(isinstance(args[0], CatalogerConduit))
                self.assertEqual(args[1], source.descriptor)
                self.assertEqual(args[2], url)

    @patch('pulp.plugins.loader.api.get_cataloger_by_id', return_value=(MockCataloger(), {}))
    def test_refresh_cancel_in_sources(self, mock_plugin):
        container = ContentContainer(path=self.tmp_dir)
        event = CancelEvent(1)
        report = container.refresh(event, force=True)
        plugin = mock_plugin.return_value[0]
        self.assertEqual(plugin.refresh.call_count, 0)
        self.assertEqual(len(report), 0)

    @patch('pulp.plugins.loader.api.get_cataloger_by_id', return_value=(MockCataloger(), {}))
    def test_refresh_cancel_in_plugin(self, mock_plugin, *unused):
        container = ContentContainer(path=self.tmp_dir)
        event = CancelEvent(3)
        report = container.refresh(event, force=True)
        plugin = mock_plugin.return_value[0]
        self.assertEqual(plugin.refresh.call_count, 1)
        self.assertEqual(len(report), 1)

    @patch('pulp.plugins.loader.api.get_cataloger_by_id', return_value=(MockCataloger(ValueError), {}))
    def test_refresh_failure(self, mock_plugin):
        container = ContentContainer(path=self.tmp_dir)
        event = Event()
        report = container.refresh(event, force=True)
        self.assertEqual(len(report), 5)
        for r in report:
            self.assertFalse(r.succeeded)
            self.assertEqual(r.added_count, 0)
            self.assertEqual(r.deleted_count, 0)
            self.assertEqual(len(r.errors), 1)
        plugin = mock_plugin.return_value[0]
        collection = ContentCatalog.get_collection()
        self.assertEqual(plugin.refresh.call_count, 5)
        self.assertEqual(collection.find().count(), 0)

    @patch('pulp.server.content.sources.model.ContentSource.refresh', side_effect=ValueError)
    def test_refresh_exception(self, mock_refresh):
        container = ContentContainer(path=self.tmp_dir)
        event = Event()
        report = container.refresh(event, force=True)
        self.assertEqual(len(report), 2)
        for r in report:
            self.assertFalse(r.succeeded)
            self.assertEqual(r.added_count, 0)
            self.assertEqual(r.deleted_count, 0)
            self.assertEqual(len(r.errors), 1)
        collection = ContentCatalog.get_collection()
        self.assertEqual(mock_refresh.call_count, 2)
        self.assertEqual(collection.find().count(), 0)

    def test_purge_orphans(self):
        _dir, cataloged = self.populate_catalog(ORPHANED, 0, 10)
        _dir, cataloged = self.populate_catalog(UNDERGROUND, 0, 10)
        _dir, cataloged = self.populate_catalog(UNIT_WORLD, 0, 10)
        collection = ContentCatalog.get_collection()
        self.assertEqual(collection.find().count(), 30)
        container = ContentContainer(path=self.tmp_dir)
        container.purge_orphans()
        self.assertEqual(collection.find().count(), 20)
        self.assertEqual(collection.find({'source_id': ORPHANED}).count(), 0)
        self.assertEqual(collection.find({'source_id': UNDERGROUND}).count(), 10)
        self.assertEqual(collection.find({'source_id': UNIT_WORLD}).count(), 10)


class TestNectarListener(TestCase):

    @patch('pulp.server.content.sources.model.ContentSource.load_all', returns={})
    def test_notification(self, *unused):
        request = Request('', {}, '', '')
        listener = MockListener()
        listener.download_started = Mock(side_effect=ValueError)
        container = ContentContainer('')
        event = Event()
        nectar_listener = NectarListener(event, Mock(), listener)
        report = Mock()
        report.data = request
        # started
        nectar_listener.download_started(report)
        listener.download_started.assert_called_with(request)
        # succeeded
        nectar_listener.download_succeeded(report)
        listener.download_succeeded.assert_called_with(request)
        # failed
        nectar_listener.download_failed(report)
        listener.download_failed.assert_called_with(request)

    @patch('pulp.server.content.sources.model.ContentSource.load_all', returns={})
    def test_notification_no_listener(self, *unused):
        request = Request('', {}, '', '')
        container = ContentContainer('')
        event = Event()
        nectar_listener = NectarListener(event, Mock())
        nectar_listener._notify = Mock()
        report = Mock()
        report.data = request
        # started
        nectar_listener.download_started(report)
        self.assertFalse(nectar_listener._notify.called)
        # succeeded
        nectar_listener.download_succeeded(report)
        self.assertFalse(nectar_listener._notify.called)
        # failed
        nectar_listener.download_failed(report)
        self.assertFalse(nectar_listener._notify.called)


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


class TestModel(TestCase):

    @patch('pulp.server.content.sources.model.ContentSource.refresh')
    def test_primary(self, mock_refresh):
        primary = model.PrimarySource(LocalFileDownloader(DownloaderConfig()))
        event = Event()
        primary.refresh(event)
        self.assertEqual(mock_refresh.call_count, 0)