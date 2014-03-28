# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from unittest import TestCase
from threading import Event

from mock import patch, Mock
from nectar.request import DownloadRequest

from pulp.server.content.sources.container import ContentContainer, NectarListener
from pulp.server.content.sources.model import PrimarySource, ContentSource, Request


class TestContainer(TestCase):

    def test_collated(self):
        source_id = 1
        request_list = []

        # simulated requests
        # 0-8 need to be downloaded and have a next source.
        # 6-7 have no next source.
        # 9-10 are already downloaded.

        for n in range(10):
            r = Mock()
            r.downloaded = n > 8
            r.destination = 'path-%d' % n
            if n < 6:
                r.next_source.return_value = ('s-%d' % source_id, 'url-%d' % n)
            else:
                r.next_source.return_value = None
            request_list.append(r)
            if n % 3 == 0:
                source_id += 1

        # test
        collated = ContentContainer.collated(request_list)

        # validation
        self.assertEqual(len(collated), 3)

        for requests in collated.values():
            for r in requests:
                self.assertTrue(isinstance(r, DownloadRequest))

        self.assertEqual(
            [s.__dict__ for s in collated['s-1']],
            [
                DownloadRequest('url-0', 'path-0', data=request_list[0]).__dict__
            ])
        self.assertEqual(
            [s.__dict__ for s in collated['s-2']],
            [
                DownloadRequest('url-1', 'path-1', data=request_list[1]).__dict__,
                DownloadRequest('url-2', 'path-2', data=request_list[2]).__dict__,
                DownloadRequest('url-3', 'path-3', data=request_list[3]).__dict__
            ])
        self.assertEqual(
            [s.__dict__ for s in collated['s-3']],
            [
                DownloadRequest('url-4', 'path-4', data=request_list[4]).__dict__,
                DownloadRequest('url-5', 'path-5', data=request_list[5]).__dict__,
            ])

    def test_collated_all_downloaded(self):
        request_list = []
        for n in range(10):
            r = Mock()
            r.downloaded = True
            request_list.append(r)

        # test
        collated = ContentContainer.collated(request_list)

        # validation
        self.assertEqual(len(collated), 0)

    @patch('pulp.server.content.sources.container.ContentSource.load_all')
    def test_construction(self, fake_load):
        path = 'path-1'

        # test
        ContentContainer(path)

        # validation
        fake_load.assert_called_with(path)

    @patch('pulp.server.content.sources.container.ContentSource.load_all', Mock())
    def test_download(self):
        sources = []
        for n in range(3):
            s = ContentSource('s-%d' % n, {})
            s.downloader = Mock()
            sources.append(s)

        request_list = []
        for n in range(6):
            r = Request('T', {}, 'url-%d' % n, 'path-%d' % n)
            r.find_sources = Mock(return_value=sources[n % 3:])
            request_list.append(r)

        collated = [
            {
                sources[0]: ['nectar-1'],
                sources[1]: ['nectar-2', 'nectar-3', 'nectar-4'],
                sources[2]: ['nectar-5', 'nectar-6']
            },
            {}
        ]
        fake_collated = Mock(side_effect=collated)

        fake_listener = Mock()
        canceled = Event()
        fake_primary = PrimarySource(Mock())

        # test
        container = ContentContainer('')
        container.refresh = Mock()
        container.collated = fake_collated
        container.download(canceled, fake_primary, request_list, fake_listener)

        # validation
        container.refresh.assert_called_with(canceled)

        for r in request_list:
            r.find_sources.assert_called_with(fake_primary, container.sources)

        for source in sources:
            source.downloader.assert_called_with()
            downloader = source.downloader()
            listener = downloader.event_listener
            self.assertEqual(listener.cancel_event, canceled)
            self.assertEqual(listener.downloader, downloader)
            self.assertEqual(listener.listener, fake_listener)
            downloader.download.assert_called_with(collated[0][source])

    @patch('pulp.server.content.sources.container.ContentSource.load_all', Mock())
    def test_download_canceled_before_collated(self):
        canceled = Event()
        canceled.set()

        # test
        container = ContentContainer('')
        container.refresh = Mock()
        container.collated = Mock()
        container.download(canceled, None, [], None)

        container.refresh.assert_called_with(canceled)

        self.assertFalse(container.collated.called)

    @patch('pulp.server.content.sources.container.ContentSource.load_all', Mock())
    def test_download_canceled_after_collated(self):
        sources = []
        for n in range(3):
            s = ContentSource('s-%d' % n, {})
            s.downloader = Mock()
            sources.append(s)

        request_list = []
        for n in range(6):
            r = Request('T', {}, 'url-%d' % n, 'path-%d' % n)
            r.find_sources = Mock(return_value=sources[n % 3:])
            request_list.append(r)

        collated = [
            {
                sources[0]: ['nectar-1'],
                sources[1]: ['nectar-2', 'nectar-3', 'nectar-4'],
                sources[2]: ['nectar-5', 'nectar-6']
            },
            {}
        ]
        fake_collated = Mock(side_effect=collated)

        fake_listener = Mock()
        canceled = Mock()
        canceled.isSet.side_effect = [False, True, True]
        fake_primary = PrimarySource(Mock())

        # test
        container = ContentContainer('')
        container.refresh = Mock()
        container.collated = fake_collated
        container.download(canceled, fake_primary, request_list, fake_listener)

        # validation
        container.refresh.assert_called_with(canceled)

        for r in request_list:
            r.find_sources.assert_called_with(fake_primary, container.sources)

        called = 0
        for s in sources:
            if s.downloader.called:
                called += 1

        self.assertEqual(called, 1)

    @patch('pulp.server.content.sources.container.ContentSource.load_all')
    @patch('pulp.server.content.sources.container.managers.content_catalog_manager')
    def test_refresh(self, fake_manager, fake_load):
        sources = {}
        for n in range(3):
            s = ContentSource('s-%d' % n, {})
            s.refresh = Mock(return_value=[n])
            s.downloader = Mock()
            sources[s.id] = s

        fake_manager().has_entries.return_value = False
        fake_load.return_value = sources

        # test
        canceled = Event()
        container = ContentContainer('')
        report = container.refresh(canceled)

        # validation
        for s in sources.values():
            s.refresh.assert_called_with(canceled)

        self.assertEqual(sorted(report), [0, 1, 2])

    @patch('pulp.server.content.sources.container.ContentSource.load_all')
    @patch('pulp.server.content.sources.container.managers.content_catalog_manager')
    def test_refresh_raised(self, fake_manager, fake_load):
        sources = {}
        for n in range(3):
            s = ContentSource('s-%d' % n, {})
            s.refresh = Mock(side_effect=ValueError('must be int'))
            s.downloader = Mock()
            sources[s.id] = s

        fake_manager().has_entries.return_value = False
        fake_load.return_value = sources

        # test
        canceled = Event()
        container = ContentContainer('')
        report = container.refresh(canceled)

        # validation
        for s in sources.values():
            s.refresh.assert_called_with(canceled)

        for r in report:
            r.errors = ['must be int']

    @patch('pulp.server.content.sources.container.ContentSource.load_all')
    @patch('pulp.server.content.sources.container.managers.content_catalog_manager')
    def test_forced_refresh(self, fake_manager, fake_load):
        sources = {}
        for n in range(3):
            s = ContentSource('s-%d' % n, {})
            s.refresh = Mock()
            sources[s.id] = s

        fake_manager().has_entries.return_value = True
        fake_load.return_value = sources

        # test
        canceled = Event()
        container = ContentContainer('')
        container.refresh(canceled, force=True)

        # validation
        for s in sources.values():
            s.refresh.assert_called_with(canceled)

    @patch('pulp.server.content.sources.container.ContentSource.load_all')
    @patch('pulp.server.content.sources.container.managers.content_catalog_manager', Mock())
    def test_refresh_canceled(self, fake_load):
        sources = {}
        for n in range(3):
            s = ContentSource('s-%d' % n, {})
            s.refresh = Mock()
            sources[s.id] = s

        fake_load.return_value = sources

        # test
        canceled = Event()
        canceled.set()
        container = ContentContainer('')
        container.refresh(canceled, force=True)

        # validation
        for s in sources.values():
            self.assertFalse(s.refresh.called)

    @patch('pulp.server.content.sources.container.ContentSource.load_all')
    @patch('pulp.server.content.sources.container.managers.content_catalog_manager')
    def test_purge_orphans(self, fake_manager, fake_load):
        fake_load.return_value = {'A': 1, 'B': 2, 'C': 3}

        # test
        container = ContentContainer('')

        # validation
        container.purge_orphans()

        fake_manager().purge_orphans.assert_called_with(fake_load.return_value.keys())


class TestNectarListener(TestCase):

    @patch('pulp.server.content.sources.container.log')
    def test_notify(self, mock_log):
        method = Mock()
        report = Mock()

        # test
        NectarListener._notify(method, report)

        # validations
        method.assert_called_with(report)

        # test (raised)
        method.side_effect = ValueError()
        NectarListener._notify(method, report)

        # validation
        mock_log.exception.assert_called_with(str(method))

    def test_construction(self):
        canceled = Event()
        downloader = Mock()
        listener = Mock()

        # test
        nectar_listener = NectarListener(canceled, downloader, listener=listener)
        self.assertEqual(nectar_listener.cancel_event, canceled)
        self.assertEqual(nectar_listener.downloader, downloader)
        self.assertEqual(nectar_listener.listener, listener)

    def test_download_started(self):
        canceled = Mock()
        canceled.isSet.return_value = False
        downloader = Mock()
        listener = Mock()
        report = Mock()
        report.data = {'A': 1}

        # test
        nectar_listener = NectarListener(canceled, downloader, listener)
        nectar_listener.download_started(report)

        # validation
        canceled.isSet.assert_called_with()
        listener.download_started.assert_called_with(report.data)

    def test_download_started_no_listener(self):
        canceled = Mock()
        canceled.isSet.return_value = False
        downloader = Mock()
        listener = None
        report = Mock()
        report.data = {'A': 1}

        # test
        nectar_listener = NectarListener(canceled, downloader, listener)
        nectar_listener.download_started(report)

        # validation
        canceled.isSet.assert_called_with()

    def test_download_started_and_canceled(self):
        canceled = Mock()
        canceled.isSet.return_value = True
        downloader = Mock()
        listener = Mock()
        report = Mock()
        report.data = {'A': 1}

        # test
        nectar_listener = NectarListener(canceled, downloader, listener)
        nectar_listener.download_started(report)

        # validation
        canceled.isSet.assert_called_with()
        self.assertFalse(listener.download_started.called)

    def test_download_succeeded(self):
        canceled = Mock()
        canceled.isSet.return_value = False
        downloader = Mock()
        listener = Mock()
        report = Mock()
        request = Mock()
        request.downloaded = False
        report.data = request

        # test
        nectar_listener = NectarListener(canceled, downloader, listener)
        nectar_listener.download_succeeded(report)

        # validation
        canceled.isSet.assert_called_with()
        self.assertTrue(request.downloaded)
        listener.download_succeeded.assert_called_with(report.data)

    def test_download_succeeded_no_listener(self):
        canceled = Mock()
        canceled.isSet.return_value = False
        downloader = Mock()
        listener = None
        report = Mock()
        request = Mock()
        request.downloaded = False
        report.data = request

        # test
        nectar_listener = NectarListener(canceled, downloader, listener)
        nectar_listener.download_succeeded(report)

        # validation
        canceled.isSet.assert_called_with()
        self.assertTrue(request.downloaded)

    def test_download_succeeded_and_canceled(self):
        canceled = Mock()
        canceled.isSet.return_value = True
        downloader = Mock()
        listener = Mock()
        report = Mock()
        report.data = Mock()

        # test
        nectar_listener = NectarListener(canceled, downloader, listener)
        nectar_listener.download_succeeded(report)

        # validation
        canceled.isSet.assert_called_with()
        self.assertFalse(listener.download_succeeded.called)

    def test_download_failed_no_sources(self):
        canceled = Mock()
        canceled.isSet.return_value = False
        downloader = Mock()
        listener = Mock()
        report = Mock()
        report.error_msg = 'just failed'
        request = Mock()
        request.errors = []
        request.has_source.return_value = False
        report.data = request

        # test
        nectar_listener = NectarListener(canceled, downloader, listener)
        nectar_listener.download_failed(report)

        # validation
        canceled.isSet.assert_called_with()
        listener.download_failed.assert_called_with(report.data)
        self.assertEqual(request.errors, [report.error_msg])

    def test_download_failed_with_sources(self):
        canceled = Mock()
        canceled.isSet.return_value = False
        downloader = Mock()
        listener = Mock()
        report = Mock()
        report.error_msg = 'just failed'
        request = Mock()
        request.errors = []
        request.has_source.return_value = True
        report.data = request

        # test
        nectar_listener = NectarListener(canceled, downloader, listener)
        nectar_listener.download_failed(report)
        self.assertEqual(request.errors, [report.error_msg])

        # validation
        canceled.isSet.assert_called_with()
        self.assertFalse(listener.download_failed.called)

    def test_download_failed_no_listener(self):
        canceled = Mock()
        canceled.isSet.return_value = False
        downloader = Mock()
        listener = None
        report = Mock()
        request = Mock()
        request.errors = []
        report.data = request

        # test
        nectar_listener = NectarListener(canceled, downloader, listener)
        nectar_listener.download_failed(report)
        self.assertEqual(request.errors, [report.error_msg])

        # validation
        canceled.isSet.assert_called_with()

    def test_download_failed_and_canceled(self):
        canceled = Mock()
        canceled.isSet.return_value = True
        downloader = Mock()
        listener = Mock()
        report = Mock()
        request = Mock()
        report.data = request

        # test
        nectar_listener = NectarListener(canceled, downloader, listener)
        nectar_listener.download_failed(report)

        # validation
        canceled.isSet.assert_called_with()
        self.assertFalse(listener.failed_succeeded.called)