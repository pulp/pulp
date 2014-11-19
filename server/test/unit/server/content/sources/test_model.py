import os
import sys
from unittest import TestCase

from mock import patch, Mock

from pulp.common.constants import PRIMARY_ID
from pulp.plugins.conduits.cataloger import CatalogerConduit
from pulp.server.content.sources import constants
from pulp.server.content.sources.model import Request, PrimarySource, ContentSource, RefreshReport
from pulp.server.content.sources.model import DownloadDetails, DownloadReport
from pulp.server.content.sources.descriptor import DEFAULT


TYPE = '1234'
TYPE_ID = 'ABCD'

DESCRIPTOR = [
    ('s-0', {  # loaded
        constants.BASE_URL: 'http://repository/s-0',
        constants.ENABLED: True,
        constants.TYPE: TYPE,
        constants.PRIORITY: '4'
    }),
    ('s-1', {  # not loaded
        constants.BASE_URL: 'http://repository/s-1',
        constants.ENABLED: False,
        constants.TYPE: TYPE,
        constants.PRIORITY: '3'
    }),
    ('s-2', {  # loaded
        constants.BASE_URL: 'http://repository/s-2',
        constants.ENABLED: True,
        constants.TYPE: TYPE,
        constants.PRIORITY: '2'
    }),
    ('s-3', {  # not loaded
        constants.BASE_URL: 'http://repository/s-3',
        constants.ENABLED: True,
        constants.TYPE: TYPE,
        constants.PRIORITY: '1'
    }),
]

CATALOG = [
    {
        constants.SOURCE_ID: DESCRIPTOR[1][0],
        constants.TYPE_ID: TYPE_ID,
        constants.UNIT_KEY: 1,
        constants.URL: os.path.join(DESCRIPTOR[1][1][constants.BASE_URL], '1')
    },
    {
        constants.SOURCE_ID: DESCRIPTOR[1][0],
        constants.TYPE_ID: TYPE_ID,
        constants.UNIT_KEY: 2,
        constants.URL: os.path.join(DESCRIPTOR[1][1][constants.BASE_URL], '2')
    },
    {
        constants.SOURCE_ID: DESCRIPTOR[3][0],
        constants.TYPE_ID: TYPE_ID,
        constants.UNIT_KEY: 3,
        constants.URL: os.path.join(DESCRIPTOR[3][1][constants.BASE_URL], '3')
    },
    {
        constants.SOURCE_ID: DESCRIPTOR[3][0],
        constants.TYPE_ID: TYPE_ID,
        constants.UNIT_KEY: 4,
        constants.URL: os.path.join(DESCRIPTOR[3][1][constants.BASE_URL], '4')
    },
    {
        constants.SOURCE_ID: 'unknown',
        constants.TYPE_ID: TYPE_ID,
        constants.UNIT_KEY: 4,
        constants.URL: os.path.join(DESCRIPTOR[3][1][constants.BASE_URL], '4')
    },
]


class FakeRefresh(object):

    def __init__(self):
        self._added = 10
        self._deleted = 1

    def __call__(self, conduit, *unused):
        conduit.added_count = self._added
        conduit.deleted_count = self._deleted
        self._added += 10
        self._deleted += 1


class TestRequest(TestCase):

    def test_construction(self):
        type_id = 'test_1'
        unit_key = {'name': 'A', 'version': '1.0'}
        destination = '/tmp/123'
        url = 'http://redhat.com/repository'

        # test

        request = Request(type_id, unit_key, url, destination)

        # validation

        self.assertEqual(request.type_id, type_id)
        self.assertEqual(request.unit_key, unit_key)
        self.assertEqual(request.url, url)
        self.assertEqual(request.destination, destination)
        self.assertFalse(request.downloaded)
        self.assertTrue(isinstance(request.sources, type(iter([]))))
        self.assertEqual(request.index, 0)
        self.assertEqual(request.errors, [])
        self.assertEqual(request.data, None)

    @patch('pulp.server.content.sources.container.managers.content_catalog_manager')
    def test_find_sources(self, fake_manager):
        type_id = 'test_1'
        unit_key = 1
        destination = '/tmp/123'
        url = 'http://redhat.com/repository'

        primary = PrimarySource(None)
        alternatives = dict([(s, ContentSource(s, d)) for s, d in DESCRIPTOR])
        fake_manager().find.return_value = CATALOG

        # test

        request = Request(type_id, unit_key, url, destination)
        request.find_sources(primary, alternatives)

        # validation

        # validate sources sorted by priority with the primary last.
        # should only have matched on s-1 and s-3.

        request.sources = list(request.sources)
        self.assertEqual(len(request.sources), 5)
        self.assertEqual(request.sources[0][0].id, 's-3')
        self.assertEqual(request.sources[0][1], CATALOG[2][constants.URL])
        self.assertEqual(request.sources[1][0].id, 's-3')
        self.assertEqual(request.sources[1][1], CATALOG[3][constants.URL])
        self.assertEqual(request.sources[2][0].id, 's-1')
        self.assertEqual(request.sources[2][1], CATALOG[0][constants.URL])
        self.assertEqual(request.sources[3][0].id, 's-1')
        self.assertEqual(request.sources[3][1], CATALOG[1][constants.URL])
        self.assertEqual(request.sources[4][0].id, primary.id)
        self.assertEqual(request.sources[4][1], url)

    def test_next_source(self):
        sources = [1, 2, 3]
        request = Request('', {}, '', '')
        request.sources = sources

        # test and validation

        for i, source in enumerate(request.sources):
            self.assertEqual(source, sources[i])


class TestContentSource(TestCase):

    @patch('os.path.isfile')
    @patch('os.listdir')
    @patch('pulp.server.content.sources.model.ConfigParser')
    @patch('pulp.server.content.sources.model.ContentSource.enabled')
    @patch('pulp.server.content.sources.model.ContentSource.is_valid')
    def test_load_all(self, fake_valid, fake_enabled, fake_parser, fake_listdir, fake_isfile):
        conf_d = '/fake/conf_d'
        files = ['one.conf', 'other']
        fake_listdir.return_value = files

        fake_valid.side_effect = [
            True,  # s-0
                   # s-1 not enabled
            True,  # s-2
            False  # s-3
        ]

        fake_isfile.side_effect = [True, False]

        fake_enabled.__get__ = Mock(side_effect=[d[1]['enabled'] for d in DESCRIPTOR])

        parser = Mock()
        parser.items.side_effect = [d[1].items() for d in DESCRIPTOR]
        parser.sections.return_value = [d[0] for d in DESCRIPTOR]
        fake_parser.return_value = parser

        # test

        sources = ContentSource.load_all(conf_d)

        # validation

        fake_listdir.assert_called_with(conf_d)
        fake_parser.assert_called_with()
        fake_parser().read.assert_called_with(os.path.join(conf_d, files[0]))

        self.assertEqual(len(sources), 2)
        self.assertTrue(DESCRIPTOR[0][0] in sources)
        self.assertTrue(DESCRIPTOR[2][0] in sources)

    def test_construction(self):
        # test
        source = ContentSource(DESCRIPTOR[0][0], DESCRIPTOR[0][1])

        # validation

        self.assertEqual(source.id, DESCRIPTOR[0][0])
        self.assertEqual(source.descriptor, DESCRIPTOR[0][1])

    @patch('pulp.server.content.sources.model.is_valid')
    def test_is_valid(self, mock_descriptor_is_valid):
        source = ContentSource('s-1', {'A': 1})
        source.get_downloader = Mock()
        source.get_cataloger = Mock()

        # Test

        valid = source.is_valid()

        # validation

        source.get_cataloger.assert_called_with()
        source.get_downloader.assert_called_with()
        mock_descriptor_is_valid.assert_called_with(source.id, source.descriptor)
        self.assertTrue(valid)

    @patch('pulp.server.content.sources.model.is_valid')
    def test_is_valid_no_plugin(self, mock_descriptor_is_valid):
        mock_descriptor_is_valid.return_value = True
        source = ContentSource('s-1', {'A': 1})
        source.get_downloader = Mock()
        source.get_cataloger = Mock(side_effect=NotImplementedError())

        # Test

        valid = source.is_valid()

        # validation

        source.get_cataloger.assert_called_with()
        self.assertFalse(source.get_downloader.called)
        self.assertTrue(mock_descriptor_is_valid.called)
        self.assertFalse(valid)

    @patch('pulp.server.content.sources.model.is_valid')
    def test_is_valid_no_downloader(self, mock_descriptor_is_valid):
        mock_descriptor_is_valid.return_value = True
        source = ContentSource('s-1', {'A': 1})
        source.get_downloader = Mock(side_effect=NotImplementedError())
        source.get_cataloger = Mock()

        # Test

        valid = source.is_valid()

        # validation

        source.get_cataloger.assert_called_with()
        source.get_downloader.assert_called_with()
        self.assertTrue(mock_descriptor_is_valid.called)
        self.assertFalse(valid)

    @patch('pulp.server.content.sources.model.is_valid')
    def test_is_valid_bad_descriptor(self, mock_descriptor_is_valid):
        source = ContentSource('s-1', {'A': 1})
        source.get_downloader = Mock()
        source.get_cataloger = Mock()
        mock_descriptor_is_valid.side_effect = ValueError()

        # Test

        valid = source.is_valid()

        # validation

        self.assertFalse(valid)

    def test_enabled(self):
        source = ContentSource('s-1', {constants.ENABLED: 'true'})
        self.assertTrue(source.enabled)
        source.descriptor[constants.ENABLED] = 'false'
        self.assertFalse(source.enabled)

    def test_priority(self):
        source = ContentSource('s-1', {constants.PRIORITY: 123})
        self.assertEqual(source.priority, 123)

    def test_expires(self):
        source = ContentSource('s-1', {constants.EXPIRES: '1h'})
        self.assertEqual(source.expires, 3600)

    def test_base_url(self):
        source = ContentSource('s-1', {constants.BASE_URL: 'http://xyz.com'})
        self.assertEqual(source.base_url, 'http://xyz.com')

    def test_max_concurrent(self):
        source = ContentSource('s-1', {constants.MAX_CONCURRENT: 123})
        self.assertEqual(source.max_concurrent, 123)

    def test_urls(self):
        base_url = 'http://xyz.com'
        paths = 'path1/ path2 path3/ \\\npath4'
        source = ContentSource('s-1', {constants.BASE_URL: base_url, constants.PATHS: paths})

        # test
        urls = source.urls

        # validation

        expected = [
            'http://xyz.com/path1/',
            'http://xyz.com/path2/',
            'http://xyz.com/path3/',
            'http://xyz.com/path4/',
        ]

        self.assertEqual(urls, expected)

    def test_urls_no_paths(self):
        base_url = 'http://xyz.com'
        source = ContentSource('s-1', {constants.BASE_URL: base_url})

        # test
        urls = source.urls

        # validation

        expected = [
            'http://xyz.com',
        ]

        self.assertEqual(urls, expected)

    def test_conduit(self):
        source = ContentSource('s-1', {constants.EXPIRES: '1h'})

        conduit = source.get_conduit()

        self.assertEqual(conduit.source_id, source.id)
        self.assertEqual(conduit.expires, 3600)
        self.assertTrue(isinstance(conduit, CatalogerConduit))

    @patch('pulp.server.content.sources.model.plugins')
    def test_cataloger(self, fake_plugins):
        plugin = Mock()
        fake_plugins.get_cataloger_by_id.return_value = plugin, {}

        # test

        source = ContentSource('s-1', {constants.TYPE: 1234})
        cataloger = source.get_cataloger()

        # validation

        fake_plugins.get_cataloger_by_id.assert_called_with(1234)
        self.assertEqual(plugin, cataloger)

    def test_downloader(self):
        url = 'http://xyz.com'
        fake_conduit = Mock()
        fake_cataloger = Mock()
        fake_downloader = Mock()
        fake_cataloger.get_downloader = Mock(return_value=fake_downloader)

        source = ContentSource('s-1', {constants.BASE_URL: url})
        source.get_conduit = Mock(return_value=fake_conduit)
        source.get_cataloger = Mock(return_value=fake_cataloger)

        # test
        downloader = source.get_downloader()

        # validation
        source.get_cataloger.assert_called_with()
        fake_cataloger.get_downloader.assert_called_with(fake_conduit, source.descriptor, url)
        self.assertEqual(downloader, fake_downloader)

    @patch('pulp.server.content.sources.model.ContentSource.urls')
    def test_refresh(self, fake_urls):
        url = 'http://xyz.com'
        urls = ['url-1', 'url-2']
        fake_urls.__get__ = Mock(return_value=urls)

        canceled = Mock()
        canceled.isSet = Mock(return_value=False)
        conduit = Mock()
        cataloger = Mock()
        cataloger.refresh.side_effect = FakeRefresh()

        source = ContentSource('s-1', {constants.BASE_URL: url})
        source.get_conduit = Mock(return_value=conduit)
        source.get_cataloger = Mock(return_value=cataloger)

        # test

        report = source.refresh(canceled)

        # validation

        self.assertEqual(canceled.isSet.call_count, len(urls))
        self.assertEqual(conduit.reset.call_count, len(urls))
        self.assertEqual(cataloger.refresh.call_count, len(urls))

        n = 0
        added = 10
        deleted = 1
        for _url in source.urls:
            cataloger.refresh.assert_any(conduit, source.descriptor, _url)
            self.assertEqual(report[n].source_id, source.id)
            self.assertEqual(report[n].url, _url)
            self.assertTrue(report[n].succeeded)
            self.assertEqual(report[n].errors, [])
            self.assertEqual(report[n].added_count, added)
            self.assertEqual(report[n].deleted_count, deleted)
            added += 10
            deleted += 1
            n += 1

    @patch('pulp.server.content.sources.model.ContentSource.urls')
    def test_refresh_canceled(self, fake_urls):
        url = 'http://xyz.com'
        urls = ['url-1', 'url-2']

        fake_urls.__get__ = Mock(return_value=urls)

        canceled = Mock()
        canceled.isSet = Mock(return_value=True)
        conduit = Mock()
        cataloger = Mock()

        source = ContentSource('s-1', {constants.BASE_URL: url})
        source.get_conduit = Mock(return_value=conduit)
        source.get_cataloger = Mock(return_value=cataloger)

        # test

        report = source.refresh(canceled)

        # validation

        self.assertEqual(canceled.isSet.call_count, 1)
        self.assertEqual(conduit.reset.call_count, 0)
        self.assertEqual(cataloger.refresh.call_count, 0)
        self.assertEqual(report, [])

    @patch('pulp.server.content.sources.model.ContentSource.urls')
    def test_refresh_raised(self, fake_urls):
        url = 'http://xyz.com'
        urls = ['url-1', 'url-2']
        fake_urls.__get__ = Mock(return_value=urls)

        canceled = Mock()
        canceled.isSet = Mock(return_value=False)
        conduit = Mock()
        cataloger = Mock()
        cataloger.refresh.side_effect = ValueError('just failed')

        source = ContentSource('s-1', {constants.BASE_URL: url})
        source.get_conduit = Mock(return_value=conduit)
        source.get_cataloger = Mock(return_value=cataloger)

        # test

        report = source.refresh(canceled)

        # validation

        self.assertEqual(canceled.isSet.call_count, len(urls))
        self.assertEqual(conduit.reset.call_count, len(urls))
        self.assertEqual(cataloger.refresh.call_count, len(urls))

        n = 0
        for _url in source.urls:
            cataloger.refresh.assert_any(conduit, source.descriptor, _url)
            self.assertEqual(report[n].source_id, source.id)
            self.assertEqual(report[n].url, _url)
            self.assertFalse(report[n].succeeded)
            self.assertEqual(report[n].errors, ['just failed'])
            self.assertEqual(report[n].added_count, 0)
            self.assertEqual(report[n].deleted_count, 0)
            n += 1

    def test_dict(self):
        descriptor = {'A': 1, 'B': 2}

        # test
        source = ContentSource('s-1', descriptor)

        # validation
        expected = {}
        expected.update(descriptor)
        expected[constants.SOURCE_ID] = source.id
        self.assertEqual(source.dict(), expected)

    def test_eq_(self):
        s1 = ContentSource('s-1', {})
        s2 = ContentSource('s-1', {})
        self.assertTrue(s1 == s2)

    def test_neq_(self):
        s1 = ContentSource('s-1', {})
        s2 = ContentSource('s-2', {})
        self.assertTrue(s1 != s2)

    def test_hash_(self):
        s1 = ContentSource('s-1', {})
        self.assertEqual(hash(s1), hash(s1.id))

    def test_gt_(self):
        s1 = ContentSource('s-1', {constants.PRIORITY: 0})
        s2 = ContentSource('s-2', {constants.PRIORITY: 1})
        self.assertTrue(s2 > s1)

    def test_lt_(self):
        s1 = ContentSource('s-1', {constants.PRIORITY: 0})
        s2 = ContentSource('s-2', {constants.PRIORITY: 1})
        self.assertTrue(s1 < s2)

    def test_sorting(self):
        s1 = ContentSource('s-1', {constants.PRIORITY: 2})
        s2 = ContentSource('s-2', {constants.PRIORITY: 1})
        s3 = ContentSource('s-3', {constants.PRIORITY: 0})

        _list = sorted([s1, s2, s3])
        self.assertEqual([s.id for s in _list], [s3.id, s2.id, s1.id])


class TestPrimarySource(TestCase):

    def test_construction(self):
        downloader = Mock()
        primary = PrimarySource(downloader)
        self.assertEqual(primary.id, PRIMARY_ID)
        self.assertEqual(primary._downloader, downloader)

    def test_downloader(self):
        downloader = Mock()
        primary = PrimarySource(downloader)
        self.assertEqual(primary.get_downloader(), downloader)

    def test_refresh(self):
        # just added for coverage
        primary = PrimarySource(None)
        primary.refresh(None)

    def test_priority(self):
        primary = PrimarySource(None)
        self.assertEqual(primary.priority, sys.maxint)

    def test_max_concurrent(self):
        primary = PrimarySource(None)
        self.assertEqual(primary.max_concurrent, int(DEFAULT[constants.MAX_CONCURRENT]))


class TestDownloadDetails(TestCase):

    def test_construction(self):
        details = DownloadDetails()
        self.assertEqual(details.total_succeeded, 0)
        self.assertEqual(details.total_failed, 0)

    def test_dict(self):
        details = DownloadDetails()
        self.assertEqual(details.dict(), {'total_failed': 0, 'total_succeeded': 0})


class TestDownloadReport(TestCase):

    def test_construction(self):
        report = DownloadReport()
        self.assertEqual(report.total_sources, 0)
        self.assertEqual(report.downloads, {})

    def test_dict(self):
        report = DownloadReport()
        report.downloads['s1'] = DownloadDetails()
        report.downloads['s2'] = DownloadDetails()
        expected = {
            'total_sources': 0,
            'downloads': {
                's1': {'total_failed': 0, 'total_succeeded': 0},
                's2': {'total_failed': 0, 'total_succeeded': 0}
            },
        }
        self.assertEqual(report.dict(), expected)


class TestRefreshReport(TestCase):

    def test_construction(self):
        source_id = 's-1'
        url = 'myurl'
        report = RefreshReport(source_id, url)
        self.assertEqual(report.source_id, source_id)
        self.assertEqual(report.url, url)
        self.assertFalse(report.succeeded)
        self.assertEqual(report.added_count, 0)
        self.assertEqual(report.deleted_count, 0)
        self.assertEqual(report.errors, [])

    def test_dict(self):
        source_id = 's-1'
        url = 'myurl'
        report = RefreshReport(source_id, url)
        report_dict = report.dict()
        self.assertEqual(report_dict['source_id'], source_id)
        self.assertEqual(report_dict['url'], url)
        self.assertFalse(report_dict['succeeded'])
        self.assertEqual(report_dict['added_count'], 0)
        self.assertEqual(report_dict['deleted_count'], 0)
        self.assertEqual(report_dict['errors'], [])
