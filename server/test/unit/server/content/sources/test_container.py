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

from Queue import Queue, Full, Empty
from collections import namedtuple

from mock import Mock, patch, call

from pulp.server.content.sources.container import (
    ContentContainer, NectarListener, Item, RequestQueue, Batch, Threaded, Serial,
    DownloadReport, NectarFeed, Tracker, DownloadFailed, DOWNLOAD_SUCCEEDED)
from pulp.server.content.sources.model import ContentSource


MODULE = 'pulp.server.content.sources.container'


class SideEffect(object):
    """
    Supports collection of side effects containing exceptions.
    """

    def __init__(self, values):
        self.values = iter(values)

    def __call__(self, *args, **kwargs):
        value = next(self.values)
        if isinstance(value, Exception):
            raise value
        else:
            return value


class TestContainer(TestCase):

    @patch(MODULE + '.ContentSource.load_all')
    def test_init(self, fake_load):
        path = 'path-1'

        # test
        container = ContentContainer(path)

        # validation
        fake_load.assert_called_with(path)
        self.assertEqual(container.sources, fake_load.return_value)
        self.assertEqual(container.threaded, True)

    @patch(MODULE + '.Serial')
    @patch(MODULE + '.PrimarySource')
    @patch(MODULE + '.ContentContainer.refresh')
    @patch(MODULE + '.ContentSource.load_all')
    def test_serial_download(self, fake_load, fake_refresh, fake_primary, fake_batch):
        path = Mock()
        downloader = Mock()
        requests = Mock()
        listener = Mock()

        _batch = Mock()
        _batch.download.return_value = 123
        fake_batch.return_value = _batch

        # test
        container = ContentContainer(path)
        container.threaded = False
        report = container.download(downloader, requests, listener)

        # validation
        fake_load.assert_called_with(path)
        fake_refresh.assert_called_with()
        fake_primary.assert_called_with(downloader)
        fake_batch.assert_called_with(fake_primary(), container, requests, listener)
        _batch.assert_called_with()
        self.assertEqual(report, _batch.return_value)

    @patch(MODULE + '.Threaded')
    @patch(MODULE + '.PrimarySource')
    @patch(MODULE + '.ContentContainer.refresh')
    @patch(MODULE + '.ContentSource.load_all')
    def test_threaded_download(self, fake_load, fake_refresh, fake_primary, fake_batch):
        path = Mock()
        downloader = Mock()
        requests = Mock()
        listener = Mock()

        _batch = Mock()
        _batch.download.return_value = 123
        fake_batch.return_value = _batch

        # test
        container = ContentContainer(path)
        report = container.download(downloader, requests, listener)

        # validation
        fake_load.assert_called_with(path)
        fake_refresh.assert_called_with()
        fake_primary.assert_called_with(downloader)
        fake_batch.assert_called_with(fake_primary(), container, requests, listener)
        _batch.assert_called_with()
        self.assertEqual(report, _batch.return_value)

    @patch(MODULE + '.ContentSource.load_all')
    @patch(MODULE + '.managers.content_catalog_manager')
    def test_refresh(self, fake_manager, fake_load):
        sources = {}
        for n in range(3):
            s = ContentSource('s-%d' % n, {})
            s.refresh = Mock(return_value=[n])
            s.get_downloader = Mock()
            sources[s.id] = s

        fake_manager().has_entries.return_value = False
        fake_load.return_value = sources

        # test
        container = ContentContainer('')
        report = container.refresh()

        # validation
        for s in sources.values():
            s.refresh.assert_called_with()

        self.assertEqual(sorted(report), [0, 1, 2])

    @patch(MODULE + '.ContentSource.load_all')
    @patch(MODULE + '.managers.content_catalog_manager')
    def test_refresh_raised(self, fake_manager, fake_load):
        sources = {}
        for n in range(3):
            s = ContentSource('s-%d' % n, {})
            s.refresh = Mock(side_effect=ValueError('must be int'))
            s.get_downloader = Mock()
            sources[s.id] = s

        fake_manager().has_entries.return_value = False
        fake_load.return_value = sources

        # test
        container = ContentContainer('')
        report = container.refresh()

        # validation
        for s in sources.values():
            s.refresh.assert_called_with()

        for r in report:
            r.errors = ['must be int']

    @patch(MODULE + '.ContentSource.load_all')
    @patch(MODULE + '.managers.content_catalog_manager')
    def test_forced_refresh(self, fake_manager, fake_load):
        sources = {}
        for n in range(3):
            s = ContentSource('s-%d' % n, {})
            s.refresh = Mock()
            sources[s.id] = s

        fake_manager().has_entries.return_value = True
        fake_load.return_value = sources

        # test
        container = ContentContainer('')
        container.refresh(force=True)

        # validation
        for s in sources.values():
            s.refresh.assert_called_with()

    @patch(MODULE + '.ContentSource.load_all')
    @patch(MODULE + '.managers.content_catalog_manager')
    def test_purge_orphans(self, fake_manager, fake_load):
        fake_load.return_value = {'A': 1, 'B': 2, 'C': 3}

        # test
        container = ContentContainer('')

        # validation
        container.purge_orphans()

        fake_manager().purge_orphans.assert_called_with(fake_load.return_value.keys())


class TestNectarListener(TestCase):

    def test_init(self):
        batch = Mock()

        # test
        listener = NectarListener(batch)

        # validation
        self.assertEqual(listener.batch, batch)

    @patch(MODULE + '.Started')
    def test_download_started(self, event):
        batch = Mock()
        batch.listener = Mock()
        report = Mock()
        report.data = Mock()

        # test
        listener = NectarListener(batch)
        listener.download_started(report)

        # validation
        event.assert_called_once_with(report.data)
        event.return_value.assert_called_once_with(batch.listener)

    @patch(MODULE + '.Succeeded')
    def test_download_succeeded(self, event):
        batch = Mock()
        batch.in_progress = Mock()
        batch.listener = Mock()
        report = Mock()
        report.data = Mock()

        # test
        listener = NectarListener(batch)
        listener.download_succeeded(report)

        # validation
        batch.in_progress.decrement.assert_called_with()
        event.assert_called_once_with(report.data)
        event.return_value.assert_called_once_with(batch.listener)
        self.assertEqual(listener.total_succeeded, 1)

    @patch(MODULE + '.Failed')
    def test_download_failed(self, event):
        batch = Mock()
        batch.listener = Mock()
        batch.dispatch.return_value = True
        batch.in_progress = Mock()
        report = Mock()
        report.data = Mock()
        report.data.errors = []
        report.error_msg = 'something bad happened'

        # test
        listener = NectarListener(batch)
        listener.download_failed(report)

        # validation)
        self.assertFalse(event.called)
        self.assertFalse(batch.in_progress.decrement.called)
        self.assertEqual(len(report.data.errors), 1)
        self.assertEqual(report.data.errors[0], report.error_msg)
        self.assertEqual(listener.total_failed, 1)

    @patch(MODULE + '.Failed')
    def test_download_failed_not_dispatched(self, event):
        batch = Mock()
        batch.listener = Mock()
        batch.dispatch.return_value = False
        report = Mock()
        report.data = Mock()
        report.data.errors = []
        report.error_msg = 'something bad happened'

        # test
        listener = NectarListener(batch)
        listener.download_failed(report)

        # validation
        event.assert_called_once_with(report.data)
        event.return_value.assert_called_once_with(batch.listener)
        self.assertEqual(len(report.data.errors), 1)
        self.assertEqual(report.data.errors[0], report.error_msg)
        self.assertEqual(listener.total_failed, 1)


class TestBatch(TestCase):

    def test_init(self):
        primary = Mock()
        container = Mock()
        requests = Mock()
        listener = Mock()

        # test
        batch = Batch(primary, container, requests, listener)

        # validation
        self.assertEqual(batch.primary, primary)
        self.assertEqual(batch.container, container)
        self.assertEqual(batch.requests, requests)
        self.assertEqual(batch.listener, listener)
        self.assertRaises(NotImplementedError, batch)


class TestSerial(TestCase):

    def test_init(self):
        primary = Mock()
        container = Mock()
        requests = Mock()
        listener = Mock()

        # test
        batch = Serial(primary, container, requests, listener)

        # validation
        self.assertEqual(batch.primary, primary)
        self.assertEqual(batch.container, container)
        self.assertEqual(batch.requests, requests)
        self.assertEqual(batch.listener, listener)

    @patch(MODULE + '.Started')
    @patch(MODULE + '.Succeeded')
    @patch(MODULE + '.Serial._download')
    def test_download_succeeded(self, download, succeeded, started):
        primary = Mock()
        sources = [
            Mock(id=1, url='u1'),
            Mock(id=2, url='u2'),
            Mock(id=3, url='u3'),
            Mock(id=4, url='u4')
        ]
        container = Mock(sources=sources)
        requests = [
            Mock(downloaded=False,
                 sources=[(s, s.url) for s in sources[0:2]]),
            Mock(downloaded=False,
                 sources=[(s, s.url) for s in sources[2:4]])
        ]
        listener = Mock()

        # test
        batch = Serial(primary, container, requests, listener)
        report = batch()

        # validation
        self.assertEqual(started.call_args_list, [call(r) for r in requests])
        self.assertEqual(started.return_value.call_count, len(requests))
        for r in requests:
            r.find_sources.assert_called_once_with(primary, sources)
        self.assertEqual(
            download.call_args_list,
            [call(r.sources[0][1], r.destination, r.sources[0][0]) for r in requests])
        self.assertEqual(succeeded.call_args_list, [call(r) for r in requests])
        self.assertEqual(succeeded.return_value.call_count, len(requests))
        self.assertEqual(report.total_sources, 4)
        self.assertEqual(len(report.downloads), 2)
        details = report.downloads[1]
        self.assertEqual(details.total_succeeded, 1)
        self.assertEqual(details.total_failed, 0)
        details = report.downloads[3]
        self.assertEqual(details.total_succeeded, 1)
        self.assertEqual(details.total_failed, 0)

    @patch(MODULE + '.Started')
    @patch(MODULE + '.Failed')
    @patch(MODULE + '.Serial._download')
    def test_download_failed(self, download, failed, started):
        download.side_effect = DownloadFailed()
        primary = Mock()
        sources = [
            Mock(id=1, url='u1'),
            Mock(id=2, url='u2'),
            Mock(id=3, url='u3'),
            Mock(id=4, url='u4')
        ]
        container = Mock(sources=sources)
        requests = [
            Mock(downloaded=False,
                 sources=[(s, s.url) for s in sources[0:2]]),
            Mock(downloaded=False,
                 sources=[(s, s.url) for s in sources[2:4]])
        ]
        listener = Mock()

        # test
        batch = Serial(primary, container, requests, listener)
        report = batch()

        # validation
        self.assertEqual(started.call_args_list, [call(r) for r in requests])
        self.assertEqual(started.return_value.call_count, len(requests))
        for r in requests:
            r.find_sources.assert_called_once_with(primary, sources)
        download_calls = []
        for r in requests:
            for s, u in r.sources:
                download_calls.append(call(u, r.destination, s))
        self.assertEqual(download.call_args_list, download_calls)
        self.assertEqual(failed.call_args_list, [call(r) for r in requests])
        self.assertEqual(failed.return_value.call_count, len(requests))
        self.assertEqual(report.total_sources, len(sources))
        self.assertEqual(len(report.downloads), len(sources))
        for s in sources:
            details = report.downloads[s.id]
            self.assertEqual(details.total_succeeded, 0)
            self.assertEqual(details.total_failed, 1)

    @patch(MODULE + '.DownloadRequest')
    def test__download(self, request):
        url = 'http://'
        destination = '/tmp/x'
        report = Mock(state=DOWNLOAD_SUCCEEDED)
        downloader = Mock()
        downloader.download_one.return_value = report
        source = Mock()
        source.get_downloader.return_value = downloader

        # test
        Serial._download(url, destination, source)

        # validation
        source.get_downloader.assert_called_once_with()
        request.assert_called_once_with(url, destination)
        downloader.download_one.assert_called_once_with(request.return_value, events=True)

    @patch(MODULE + '.DownloadRequest')
    def test__download_failed(self, request):
        url = 'http://'
        destination = '/tmp/x'
        report = Mock(state=None)
        downloader = Mock()
        downloader.download_one.return_value = report
        source = Mock()
        source.get_downloader.return_value = downloader

        # test
        self.assertRaises(DownloadFailed, Serial._download, url, destination, source)

        # validation
        source.get_downloader.assert_called_once_with()
        request.assert_called_once_with(url, destination)
        downloader.download_one.assert_called_once_with(request.return_value, events=True)


class TestThreaded(TestCase):

    @patch(MODULE + '.RLock')
    def test_init(self, fake_lock):
        primary = Mock()
        container = Mock()
        requests = Mock()
        listener = Mock()

        # test
        batch = Threaded(primary, container, requests, listener)

        # validation
        self.assertEqual(batch._mutex, fake_lock())
        self.assertEqual(batch.primary, primary)
        self.assertEqual(batch.container, container)
        self.assertEqual(batch.requests, requests)
        self.assertEqual(batch.listener, listener)
        self.assertEqual(len(batch.queues), 0)
        self.assertTrue(isinstance(batch.in_progress, Tracker))
        self.assertTrue(isinstance(batch.queues, dict))

    @patch(MODULE + '.RLock', Mock())
    @patch(MODULE + '.Tracker.decrement')
    @patch(MODULE + '.Item')
    @patch(MODULE + '.Threaded.find_queue')
    def test_dispatch(self, fake_find, fake_item, fake_decrement):
        fake_queue = Mock()
        fake_request = Mock()
        sources = [(Mock(), 'http://')]
        fake_request.sources = iter(sources)
        fake_find.return_value = fake_queue
        # test
        batch = Threaded(None, None, None, None)
        dispatched = batch.dispatch(fake_request)

        # validation
        fake_find.assert_called_with(sources[0][0])
        fake_item.assert_called_with(fake_request, sources[0][1])
        fake_queue.put.assert_called_with(fake_item())
        self.assertTrue(dispatched)
        self.assertFalse(fake_decrement.called)

    @patch(MODULE + '.RLock', Mock())
    @patch(MODULE + '.Threaded.find_queue')
    @patch(MODULE + '.Tracker.decrement')
    def test_dispatch_no_remaining_sources(self, fake_decrement, fake_find):
        fake_queue = Mock()
        fake_request = Mock()
        fake_request.sources = iter([])
        fake_find.return_value = fake_queue

        # test
        batch = Threaded(None, None, None, None)
        dispatched = batch.dispatch(fake_request)

        # validation
        fake_decrement.assert_called_once_with()
        self.assertFalse(dispatched)
        self.assertFalse(fake_queue.put.called)
        self.assertFalse(fake_find.called)

    @patch(MODULE + '.RLock')
    @patch(MODULE + '.Threaded._add_queue')
    def test_find_queue(self, fake_add, fake_lock):
        fake_source = Mock()
        fake_source.id = 'fake-id'
        fake_lock.__enter__ = Mock()
        fake_lock.__exit__ = Mock()

        # test
        batch = Threaded(None, None, None, None)
        batch.queues[fake_source.id] = Mock()
        queue = batch.find_queue(fake_source)

        # validation
        self.assertFalse(fake_add.called)
        self.assertEqual(queue, batch.queues[fake_source.id])

    @patch(MODULE + '.RLock')
    @patch(MODULE + '.Threaded._add_queue')
    def test_find_queue_not_found(self, fake_add, fake_lock):
        fake_source = Mock()
        fake_source.id = 'fake-id'
        fake_lock.__enter__ = Mock()
        fake_lock.__exit__ = Mock()

        # test
        batch = Threaded(None, None, None, None)
        queue = batch.find_queue(fake_source)

        # validation
        fake_add.assert_called_with(fake_source)
        self.assertEqual(batch._mutex.__enter__.call_count, 1)
        self.assertEqual(batch._mutex.__exit__.call_count, 1)
        self.assertEqual(queue, fake_add())

    @patch(MODULE + '.RLock', Mock())
    @patch(MODULE + '.NectarListener')
    @patch(MODULE + '.RequestQueue')
    def test_add_queue(self, fake_queue, fake_listener):
        fake_source = Mock()
        fake_source.id = 'fake-id'
        fake_queue().downloader = Mock()

        # test
        batch = Threaded(None, None, None, None)
        queue = batch._add_queue(fake_source)

        # validation
        fake_queue.assert_called_with(fake_source)
        fake_listener.assert_called_with(batch)
        fake_queue().start.assert_called_with()
        self.assertEqual(fake_queue().downloader.event_listener, fake_listener())
        self.assertEqual(batch.queues[fake_source.id], fake_queue())
        self.assertEqual(queue, fake_queue())

    @patch(MODULE + '.Tracker.wait')
    @patch(MODULE + '.Threaded.dispatch')
    def test_download(self, fake_dispatch, fake_wait):
        primary = Mock()
        sources = [Mock(), Mock()]
        container = Mock(sources=sources)
        requests = [Mock(), Mock(), Mock()]

        queue_1 = Mock()
        queue_1.downloader = Mock()
        queue_1.downloader.event_listener = Mock()
        queue_1.downloader.event_listener.total_succeeded = 100
        queue_1.downloader.event_listener.total_failed = 3
        queue_2 = Mock()
        queue_2.downloader = Mock()
        queue_2.downloader.event_listener = Mock()
        queue_2.downloader.event_listener.total_succeeded = 200
        queue_2.downloader.event_listener.total_failed = 10

        # test
        batch = Threaded(primary, container, iter(requests), None)
        batch.queues = {'source-1': queue_1, 'source-2': queue_2}  # simulated
        report = batch()

        # validation
        # initial dispatch
        for request in requests:
            request.find_sources.assert_called_with(primary, sources)
        calls = fake_dispatch.call_args_list
        self.assertEqual(len(calls), len(requests))
        for i, request in enumerate(requests):
            self.assertEqual(calls[i][0][0], requests[i])
        # wait
        fake_wait.assert_called_with(len(requests))
        # queue shutdown
        for queue in batch.queues.values():
            queue.put.assert_called_with(None)
            queue.halt.assert_called_with()
            queue.join.assert_called_with()
        # report
        self.assertTrue(isinstance(report, DownloadReport))
        self.assertEqual(len(report.downloads), 2)
        self.assertEqual(report.downloads['source-1'].total_succeeded, 100)
        self.assertEqual(report.downloads['source-1'].total_failed, 3)
        self.assertEqual(report.downloads['source-2'].total_succeeded, 200)
        self.assertEqual(report.downloads['source-2'].total_failed, 10)

    @patch(MODULE + '.Tracker.wait')
    @patch(MODULE + '.Threaded.dispatch')
    def test_download_nothing(self, fake_dispatch, fake_wait):
        primary = Mock()
        container = Mock(sources=[])
        requests = []

        # test
        canceled = Mock()
        canceled.is_set.return_value = False
        batch = Threaded(primary, container, iter(requests), None)
        report = batch()

        # validation
        # initial dispatch
        self.assertFalse(fake_dispatch.called)
        self.assertTrue(isinstance(report, DownloadReport))
        self.assertEqual(len(report.downloads), 0)
        fake_wait.assert_called_once_with(0)

    @patch(MODULE + '.Tracker.wait')
    @patch(MODULE + '.Threaded.dispatch')
    def test_download_with_exception(self, fake_dispatch, fake_wait):
        primary = Mock()
        fake_dispatch.side_effect = ValueError()
        sources = [Mock(), Mock()]
        container = Mock(sources=sources)
        requests = [Mock(), Mock(), Mock()]

        # test
        batch = Threaded(primary, container, iter(requests), None)
        batch.queues = {'source-1': Mock(), 'source-2': Mock()}  # simulated
        self.assertRaises(ValueError, batch)

        # validation
        fake_wait.assert_called_once_with(0)
        for queue in batch.queues.values():
            queue.put.assert_called_with(None)
            queue.halt.assert_called_with()
            queue.join.assert_called_with()


class TestRequestQueue(TestCase):

    @patch(MODULE + '.Thread', new=Mock())
    @patch(MODULE + '.Thread.setDaemon')
    @patch(MODULE + '.Queue')
    def test_init(self, fake_queue, fake_setDaemon):
        source = Mock()
        source.id = 'fake_id'
        source.max_concurrent = 10

        # test
        queue = RequestQueue(source)
        queue.setDaemon = Mock()

        # validation
        fake_queue.assert_called_with(source.max_concurrent)
        fake_setDaemon.assert_called_with(True)
        self.assertEqual(queue._halted, False)
        self.assertEqual(queue.queue, fake_queue())
        self.assertEqual(queue.downloader, source.get_downloader())

    @patch(MODULE + '.Thread', new=Mock())
    @patch(MODULE + '.Queue')
    def test_put(self, fake_queue):
        # test
        item = Mock()
        queue = RequestQueue(Mock())
        queue.put(item)

        # validation
        fake_queue().put.assert_called_with(item, timeout=3)

    @patch(MODULE + '.Thread', new=Mock())
    @patch(MODULE + '.Queue')
    def test_put_halted(self, fake_queue):
        # test
        item = Mock()
        queue = RequestQueue(Mock())
        queue.halt()
        queue.put(item)

        # validation
        self.assertFalse(fake_queue().put.called)

    @patch(MODULE + '.Thread', new=Mock())
    @patch(MODULE + '.Queue')
    def test_put_full(self, fake_queue):
        fake_queue().put.side_effect = SideEffect([Full(), Full(), None])

        # test
        item = Mock()
        queue = RequestQueue(Mock())
        queue.put(item)

        # validation
        self.assertEqual(fake_queue().put.call_count, 3)

    @patch(MODULE + '.Thread', new=Mock())
    @patch(MODULE + '.Queue')
    def test_get(self, fake_queue):
        fake_queue().get.return_value = 123

        # test
        queue = RequestQueue(Mock())
        item = queue.get()

        # validation
        fake_queue().get.assert_called_with(timeout=3)
        self.assertEqual(item, 123)

    @patch(MODULE + '.Thread', new=Mock())
    @patch(MODULE + '.Queue')
    def test_get_halted(self, fake_queue):
        # test
        queue = RequestQueue(Mock())
        queue.halt()
        item = queue.get()

        # validation
        self.assertFalse(fake_queue().get.called)
        self.assertEqual(item, None)

    @patch(MODULE + '.Thread', new=Mock())
    @patch(MODULE + '.Queue')
    def test_get_empty(self, fake_queue):
        fake_queue().get.side_effect = SideEffect([Empty(), Empty(), 123])

        # test
        queue = RequestQueue(Mock())
        item = queue.get()

        # validation
        self.assertEqual(fake_queue().get.call_count, 3)
        self.assertEqual(item, 123)

    @patch(MODULE + '.Thread', new=Mock())
    @patch(MODULE + '.Queue', Mock())
    @patch(MODULE + '.NectarFeed')
    def test_run(self, fake_feed):
        # test
        queue = RequestQueue(Mock())
        queue.run()

        # validation
        queue.downloader.download.assert_called_with(fake_feed())

    @patch(MODULE + '.Thread', new=Mock())
    @patch(MODULE + '.Queue', Mock())
    @patch(MODULE + '.RequestQueue.drain')
    @patch(MODULE + '.NectarFeed')
    def test_run_with_exception(self, fake_feed, fake_drain):
        # test
        queue = RequestQueue(Mock())
        queue.downloader.download.side_effect = ValueError()
        queue.run()

        # validation
        queue.downloader.download.assert_called_with(fake_feed())
        fake_drain.assert_called_with()

    @patch(MODULE + '.Thread', new=Mock())
    @patch(MODULE + '.Queue', Mock())
    @patch(MODULE + '.NectarDownloadReport.from_download_request')
    @patch(MODULE + '.NectarFeed')
    def test_drain(self, fake_feed, fake_from):
        queued = [1, 2, 3]
        fake_feed.return_value = queued
        fake_from.side_effect = queued

        # test
        queue = RequestQueue(Mock())
        queue.drain()

        # validation
        calls = fake_from.call_args_list
        self.assertEqual(len(calls), len(queued))
        for i, request in enumerate(queued):
            self.assertEqual(calls[i][0][0], request)
        calls = queue.downloader.fire_download_failed.call_args_list
        for i, request in enumerate(queued):
            self.assertEqual(calls[i][0][0], request)

    @patch(MODULE + '.Thread', new=Mock())
    @patch(MODULE + '.Queue', Mock())
    def test_halt(self):
        # test
        queue = RequestQueue(Mock())
        queue.halt()

        # validation
        self.assertTrue(queue._halted)


class TestNectarFeed(TestCase):

    def test_init(self):
        queue = Mock()

        # test
        feed = NectarFeed(queue)

        # validation
        self.assertEqual(feed.queue, queue)

    @patch(MODULE + '.DownloadRequest')
    def test_iter(self, fake_request):
        req = namedtuple('Request', ['destination'])
        queued = [
            Item(req(1), 2),
            Item(req(3), 4),
            Item(req(5), 6),
            None
        ]
        fake_queue = Mock()
        fake_queue.get.side_effect = queued
        fake_request.side_effect = [1, 2, 3]

        # test
        feed = NectarFeed(fake_queue)
        fetched = list(feed)

        # validation
        fake_queue.get.assert_called_with()
        calls = fake_request.call_args_list
        self.assertEqual(len(calls), len(queued) - 1)
        for i, item in enumerate(queued[:-1]):
            self.assertEqual(calls[i][0][0], item.url)
            self.assertEqual(calls[i][0][1], item.request.destination)
            self.assertEqual(calls[i][1], dict(data=item.request))
        self.assertEqual(fetched, [1, 2, 3])


class TestTracker(TestCase):

    def test_init(self):
        # test
        tracker = Tracker()

        # validation
        self.assertTrue(isinstance(tracker.queue, Queue))

    @patch(MODULE + '.Queue.put')
    def test_decrement(self, fake_put):
        # test
        tracker = Tracker()
        tracker.decrement()

        # validation
        fake_put.assert_called_once_with(0)

    @patch(MODULE + '.Queue.get')
    def test_wait(self, fake_get):
        events = [0, 0, 0]
        fake_get.side_effect = events

        # test
        n = len(events)
        tracker = Tracker()
        tracker.wait(n)

        # validation
        self.assertEqual(fake_get.call_count, n)

    def test_wait_value_error(self):
        # test
        tracker = Tracker()
        self.assertRaises(ValueError, tracker.wait, -1)

    @patch(MODULE + '.Queue.get')
    def test_wait_raising_empty(self, fake_get):
        tokens = [Empty(), 0, 0, 0]

        fake_get.side_effect = SideEffect(tokens)

        # test
        tracker = Tracker()
        tracker.wait(len(tokens) - 1)

        # validation
        self.assertEqual(fake_get.call_count, len(tokens))
