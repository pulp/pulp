from uuid import uuid4
from tempfile import mkdtemp
from threading import Event
from unittest import TestCase
import os
import shutil

from mock import patch, Mock
from nectar.config import DownloaderConfig
from nectar.downloaders.local import LocalFileDownloader
from nectar.downloaders.threaded import HTTPThreadedDownloader

from pulp.common.constants import PRIMARY_ID
from pulp.plugins.loader import api as plugins
from pulp.plugins.conduits.cataloger import CatalogerConduit
from pulp.server.db import connection
from pulp.server.db.model.content import ContentCatalog
from pulp.server.content.sources import ContentContainer, Request, ContentSource, Listener
from pulp.server.content.sources.descriptor import nectar_config
from pulp.server.managers import factory as managers


PRIMARY = 'primary'
UNIT_WORLD = 'unit-world'
UNIT_WORLD_SECURE = 'unit-world-secure'
UNDERGROUND = 'underground-content'
ORPHANED = 'orphaned'

TYPE_ID = 'rpm'
EXPIRES = 600

HEADERS = {'HEADER_1': 'LetMeIn'}


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

OTHER_SOURCES = (DISABLED, MOST_SECURE)


class FakeCataloger(object):

    def __init__(self, exception=None):
        self.exception = exception
        self.refresh = Mock(side_effect=self._refresh)

    @patch('nectar.config.DownloaderConfig._process_ssl_settings', Mock())
    def get_downloader(self, conduit, config, url):
        if url.startswith('http'):
            return HTTPThreadedDownloader(nectar_config(config))
        if url.startswith('file'):
            return LocalFileDownloader(nectar_config(config))
        raise ValueError('unsupported url')

    def _refresh(self, conduit, *unused):
        conduit.added_count = 100
        if self.exception:
            raise self.exception


class TestListener(Listener):

    def __init__(self, canceled, threshold):
        self.canceled = canceled
        self.threshold = threshold
        self.calls = 0

    def download_started(self, request):
        self.calls += 1
        if self.calls > self.threshold:
            self.canceled.set()


class ContainerTest(TestCase):

    @classmethod
    def setUpClass(cls):
        connection.initialize(name='pulp_unittest')
        managers.initialize()

    def setUp(self):
        super(ContainerTest, self).setUp()
        ContentCatalog.get_collection().remove()
        self.tmp_dir = mkdtemp()
        self.downloaded = os.path.join(self.tmp_dir, 'downloaded')
        os.makedirs(self.downloaded)
        self.add_sources()
        plugins._create_manager()
        plugins._MANAGER.catalogers.add_plugin('yum', FakeCataloger, {})

    def tearDown(self):
        super(ContainerTest, self).tearDown()
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
        urls = underground.urls
        self.assertEqual(len(urls), 4)
        self.assertEqual(urls[0], 'file:///underground/fedora/18/x86_64/')
        self.assertEqual(urls[1], 'file:///underground/fedora/18/i386/')
        self.assertEqual(urls[2], 'file:///underground/fedora/19/x86_64/')
        self.assertEqual(urls[3], 'file:///underground/fedora/19/i386/')


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
        listener = Mock()
        container = ContentContainer(path=self.tmp_dir)
        container.refresh = Mock()
        event = Event()

        # test
        report = container.download(event, downloader, request_list, listener)

        # validation
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
        self.assertEqual(report.total_sources, 2)
        self.assertEqual(len(report.downloads), 2)
        self.assertEqual(report.downloads[PRIMARY_ID].total_succeeded, 9)
        self.assertEqual(report.downloads[PRIMARY_ID].total_failed, 0)
        self.assertEqual(report.downloads[UNIT_WORLD].total_succeeded, 10)
        self.assertEqual(report.downloads[UNIT_WORLD].total_failed, 0)

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
        listener = Mock()
        container = ContentContainer(path=self.tmp_dir)
        container.refresh = Mock()
        event = Event()

        # test
        report = container.download(event, downloader, request_list, listener)

        # validation
        # unit-world
        for i in range(0, 10):
            request = request_list[i]
            self.assertTrue(request.downloaded, msg='URL: %s' % request.url)
            self.assertEqual(len(request.errors), 1)
            with open(request.destination) as fp:
                s = fp.read()
                self.assertTrue(UNDERGROUND in s)
        # primary
        for i in range(11, len(request_list)):
            request = request_list[i]
            self.assertTrue(request.downloaded, msg='URL: %s' % request.url)
            self.assertEqual(len(request.errors), 0)
            with open(request.destination) as fp:
                s = fp.read()
                self.assertTrue(PRIMARY in s)
        self.assertEqual(report.total_sources, 2)
        self.assertEqual(len(report.downloads), 3)
        self.assertEqual(report.downloads[PRIMARY_ID].total_succeeded, 9)
        self.assertEqual(report.downloads[PRIMARY_ID].total_failed, 0)
        self.assertEqual(report.downloads[UNDERGROUND].total_succeeded, 10)
        self.assertEqual(report.downloads[UNDERGROUND].total_failed, 0)
        self.assertEqual(report.downloads[UNIT_WORLD].total_succeeded, 0)
        self.assertEqual(report.downloads[UNIT_WORLD].total_failed, 10)


class TestDownloadCancel(ContainerTest):

    def test_download(self):
        request_list = []
        _dir, cataloged = self.populate_catalog(ORPHANED, 0, 1000)
        _dir, cataloged = self.populate_catalog(UNIT_WORLD, 0, 1000)
        _dir = self.populate_content(PRIMARY, 0, 2000)
        # unit-world
        for n in range(0, 1000):
            request = Request(
                cataloged[n].type_id,
                cataloged[n].unit_key,
                'file://%s/unit_%d' % (_dir, n),
                os.path.join(self.downloaded, 'unit_%d' % n))
            request_list.append(request)
        # primary
        for n in range(1001, 2000):
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
        event = Event()
        threshold = len(request_list) * 0.80  # cancel after 80% started
        downloader = LocalFileDownloader(DownloaderConfig())
        listener = TestListener(event, threshold)
        container = ContentContainer(path=self.tmp_dir)
        container.refresh = Mock()

        # test
        report = container.download(event, downloader, request_list, listener)

        # validation
        self.assertEqual(report.total_sources, 2)
        self.assertEqual(len(report.downloads), 2)
        self.assertTrue(0 < report.downloads[PRIMARY_ID].total_succeeded < 999)
        self.assertEqual(report.downloads[PRIMARY_ID].total_failed, 0)
        self.assertEqual(report.downloads[UNIT_WORLD].total_succeeded, 1000)
        self.assertEqual(report.downloads[UNIT_WORLD].total_failed, 0)

    def test_download_uncomplete_dispatch(self):
        request_list = []
        _dir, cataloged = self.populate_catalog(ORPHANED, 0, 1000)
        _dir, cataloged = self.populate_catalog(UNIT_WORLD, 0, 1000)
        _dir = self.populate_content(PRIMARY, 0, 2000)
        # unit-world
        for n in range(0, 1000):
            request = Request(
                cataloged[n].type_id,
                cataloged[n].unit_key,
                'file://%s/unit_%d' % (_dir, n),
                os.path.join(self.downloaded, 'unit_%d' % n))
            request_list.append(request)
        # primary
        for n in range(1001, 2000):
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
        event = Event()
        threshold = 0
        downloader = LocalFileDownloader(DownloaderConfig())
        listener = TestListener(event, threshold)
        container = ContentContainer(path=self.tmp_dir)
        container.refresh = Mock()

        # test
        report = container.download(event, downloader, request_list, listener)

        # validation
        self.assertEqual(report.total_sources, 2)
        self.assertEqual(len(report.downloads), 1)
        self.assertTrue(0 < report.downloads[UNIT_WORLD].total_succeeded < 10)
        self.assertEqual(report.downloads[UNIT_WORLD].total_failed, 0)

    def test_download_with_errors(self):
        request_list = []
        _dir, cataloged = self.populate_catalog(ORPHANED, 0, 1000)
        _dir, cataloged = self.populate_catalog(UNDERGROUND, 0, 1000)
        _dir, cataloged = self.populate_catalog(UNIT_WORLD, 0, 1000)
        shutil.rmtree(_dir)
        _dir = self.populate_content(PRIMARY, 0, 2000)
        # unit-world
        for n in range(0, 1000):
            request = Request(
                cataloged[n].type_id,
                cataloged[n].unit_key,
                'file://%s/unit_%d' % (_dir, n),
                os.path.join(self.downloaded, 'unit_%d' % n))
            request_list.append(request)
        # primary
        for n in range(1001, 2000):
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
        event = Event()
        threshold = len(request_list) * 0.10  # cancel after 10% started
        listener = TestListener(event, threshold)
        container = ContentContainer(path=self.tmp_dir)
        container.refresh = Mock()

        # test
        report = container.download(event, downloader, request_list, listener)

        # validation
        self.assertEqual(report.total_sources, 2)
        self.assertEqual(len(report.downloads), 2)
        self.assertTrue(0 < report.downloads[UNDERGROUND].total_succeeded < 500)
        self.assertEqual(report.downloads[UNDERGROUND].total_failed, 0)
        self.assertEqual(report.downloads[UNIT_WORLD].total_succeeded, 0)
        self.assertTrue(0 < report.downloads[UNIT_WORLD].total_failed < 1000)


class TestRefreshing(ContainerTest):

    @patch('pulp.plugins.loader.api.get_cataloger_by_id', return_value=(FakeCataloger(), {}))
    def test_refresh(self, mock_plugin):
        container = ContentContainer(path=self.tmp_dir)
        event = Event()

        # test
        report = container.refresh(event, force=True)

        # validation
        plugin = mock_plugin.return_value[0]
        self.assertEqual(plugin.refresh.call_count, 5)
        self.assertEqual(len(report), 5)
        for r in report:
            self.assertTrue(r.succeeded)
            self.assertEqual(r.added_count, 100)
            self.assertEqual(r.deleted_count, 0)
        calls = iter(plugin.refresh.call_args_list)
        for source in ContentSource.load_all(self.tmp_dir).values():
            for url in source.urls:
                args = calls.next()[0]
                self.assertTrue(isinstance(args[0], CatalogerConduit))
                self.assertEqual(args[1], source.descriptor)
                self.assertEqual(args[2], url)

    @patch('pulp.plugins.loader.api.get_cataloger_by_id', return_value=(FakeCataloger(ValueError),
           {}))
    def test_refresh_failure(self, mock_plugin):
        container = ContentContainer(path=self.tmp_dir)
        event = Event()

        # test
        report = container.refresh(event, force=True)

        # validation
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

        # test
        report = container.refresh(event, force=True)

        # validation
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

        # test
        container.purge_orphans()

        # validation
        self.assertEqual(collection.find().count(), 20)
        self.assertEqual(collection.find({'source_id': ORPHANED}).count(), 0)
        self.assertEqual(collection.find({'source_id': UNDERGROUND}).count(), 10)
        self.assertEqual(collection.find({'source_id': UNIT_WORLD}).count(), 10)
