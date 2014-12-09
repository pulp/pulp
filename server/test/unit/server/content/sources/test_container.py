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

import inspect

from unittest import TestCase

from Queue import Queue, Full, Empty
from collections import namedtuple

from mock import patch, Mock

from pulp.server.content.sources.container import (
    ContentContainer, NectarListener, Item, RequestQueue, Batch, DownloadReport,
    Listener, NectarFeed, Tracker)
from pulp.server.content.sources.model import ContentSource


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

    @patch('pulp.server.content.sources.container.ContentSource.load_all')
    def test_construction(self, fake_load):
        path = 'path-1'

        # test
        ContentContainer(path)

        # validation
        fake_load.assert_called_with(path)

    @patch('pulp.server.content.sources.container.Batch')
    @patch('pulp.server.content.sources.container.PrimarySource')
    @patch('pulp.server.content.sources.container.ContentContainer.refresh')
    @patch('pulp.server.content.sources.container.ContentSource.load_all')
    def test_download(self, fake_load, fake_refresh, fake_primary, fake_batch):
        path = Mock()
        downloader = Mock()
        requests = Mock()
        listener = Mock()
        canceled = Mock()
        canceled.is_set.return_value = False

        _batch = Mock()
        _batch.download.return_value = 123
        fake_batch.return_value = _batch

        # test
        container = ContentContainer(path)
        report = container.download(canceled, downloader, requests, listener)

        # validation
        fake_load.assert_called_with(path)
        fake_refresh.assert_called_with(canceled)
        fake_primary.assert_called_with(downloader)
        fake_batch.assert_called_with(canceled, fake_primary(), fake_load(), requests, listener)
        fake_batch().download.assert_called_with()
        self.assertEqual(report, _batch.download.return_value)

    @patch('pulp.server.content.sources.container.ContentSource.load_all')
    @patch('pulp.server.content.sources.container.managers.content_catalog_manager')
    def test_refresh(self, fake_manager, fake_load):
        sources = {}
        canceled = Mock()
        canceled.is_set.return_value = False
        for n in range(3):
            s = ContentSource('s-%d' % n, {})
            s.refresh = Mock(return_value=[n])
            s.get_downloader = Mock()
            sources[s.id] = s

        fake_manager().has_entries.return_value = False
        fake_load.return_value = sources

        # test
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
        canceled = Mock()
        canceled.is_set.return_value = False
        for n in range(3):
            s = ContentSource('s-%d' % n, {})
            s.refresh = Mock(side_effect=ValueError('must be int'))
            s.get_downloader = Mock()
            sources[s.id] = s

        fake_manager().has_entries.return_value = False
        fake_load.return_value = sources

        # test
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
        canceled = Mock()
        canceled.is_set.return_value = False
        for n in range(3):
            s = ContentSource('s-%d' % n, {})
            s.refresh = Mock()
            sources[s.id] = s

        fake_manager().has_entries.return_value = True
        fake_load.return_value = sources

        # test
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
        canceled = Mock()
        canceled.is_set.return_value = True
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
    def test_forward(self, mock_log):
        method = Mock()
        report = Mock()

        # test
        NectarListener._forward(method, report)

        # validations
        method.assert_called_with(report)

        # test (raised)
        method.side_effect = ValueError()
        NectarListener._forward(method, report)

        # validation
        mock_log.exception.assert_called_with(str(method))

    def test_construction(self):
        batch = Mock()

        # test
        listener = NectarListener(batch)

        # validation
        self.assertEqual(listener.batch, batch)

    def test_download_started(self):
        batch = Mock()
        batch.is_canceled = False
        batch.listener = Mock()
        report = Mock()
        report.data = Mock()

        # test
        listener = NectarListener(batch)
        listener.download_started(report)

        # validation
        batch.listener.download_started.assert_called_with(report.data)

    def test_download_started_no_listener(self):
        batch = Mock()
        batch.is_canceled = False
        batch.listener = Mock()
        batch.listener.__nonzero__ = Mock(return_value=False)
        report = Mock()
        report.data = Mock()

        # test
        listener = NectarListener(batch)
        listener.download_started(report)

        # validation
        self.assertFalse(batch.listener.download_started.called)

    def test_download_started_canceled(self):
        batch = Mock()
        batch.is_canceled = True
        batch.listener = Mock()
        report = Mock()
        report.data = Mock()

        # test
        listener = NectarListener(batch)
        listener.download_started(report)

        # validation
        self.assertFalse(batch.listener.download_started.called)

    def test_download_succeeded(self):
        batch = Mock()
        batch.is_canceled = False
        batch.in_progress = Mock()
        batch.listener = Mock()
        report = Mock()
        report.data = Mock()

        # test
        listener = NectarListener(batch)
        listener.download_succeeded(report)

        # validation
        batch.in_progress.decrement.assert_called_with()
        batch.listener.download_succeeded.assert_called_with(report.data)
        self.assertEqual(listener.total_succeeded, 1)

    def test_download_succeeded_no_listener(self):
        batch = Mock()
        batch.is_canceled = False
        batch.listener = Mock()
        batch.listener.__nonzero__ = Mock(return_value=False)
        report = Mock()
        report.data = Mock()

        # test
        listener = NectarListener(batch)
        listener.download_succeeded(report)

        # validation
        batch.in_progress.decrement.assert_called_with()
        self.assertFalse(batch.listener.download_succeeded.called)
        self.assertEqual(listener.total_succeeded, 1)

    def test_download_succeeded_canceled(self):
        batch = Mock()
        batch.is_canceled = True
        batch.listener = Mock()
        report = Mock()
        report.data = Mock()

        # test
        listener = NectarListener(batch)
        listener.download_succeeded(report)

        # validation
        self.assertFalse(batch.finished.called)
        self.assertFalse(batch.listener.download_succeeded.called)
        self.assertEqual(listener.total_succeeded, 1)

    def test_download_failed(self):
        batch = Mock()
        batch.is_canceled = False
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

        # validation
        batch.dispatch.assert_called_with(report.data)
        self.assertFalse(batch.listener.download_failed.called)
        self.assertFalse(batch.in_progress.decrement.called)
        self.assertEqual(len(report.data.errors), 1)
        self.assertEqual(report.data.errors[0], report.error_msg)
        self.assertEqual(listener.total_failed, 1)

    def test_download_failed_not_dispatched(self):
        batch = Mock()
        batch.is_canceled = False
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
        batch.dispatch.assert_called_with(report.data)
        batch.listener.download_failed.assert_called_with(report.data)
        self.assertEqual(len(report.data.errors), 1)
        self.assertEqual(report.data.errors[0], report.error_msg)
        self.assertEqual(listener.total_failed, 1)

    def test_download_failed_canceled(self):
        batch = Mock()
        batch.is_canceled = True
        batch.listener = Mock()
        report = Mock()
        report.data = Mock()
        report.data.errors = []
        report.error_msg = 'something bad happened'

        # test
        listener = NectarListener(batch)
        listener.download_failed(report)

        # validation
        self.assertFalse(batch.dispatch.called)
        self.assertFalse(batch.listener.download_failed.called)
        self.assertEqual(len(report.data.errors), 0)
        self.assertEqual(listener.total_failed, 1)

    def test_download_failed_not_dispatched_no_listener(self):
        batch = Mock()
        batch.is_canceled = False
        batch.listener = Mock()
        batch.listener.__nonzero__ = Mock(return_value=False)
        batch.dispatch.return_value = False
        report = Mock()
        report.data = Mock()
        report.data.errors = []
        report.error_msg = 'something bad happened'

        # test
        listener = NectarListener(batch)
        listener.download_failed(report)

        # validation
        batch.dispatch.assert_called_with(report.data)
        self.assertFalse(batch.listener.download_failed.called)
        self.assertEqual(len(report.data.errors), 1)
        self.assertEqual(report.data.errors[0], report.error_msg)
        self.assertEqual(listener.total_failed, 1)


class TestBatch(TestCase):

    @patch('pulp.server.content.sources.container.RLock')
    def test_construction(self, fake_lock):
        primary = Mock()
        sources = Mock()
        requests = Mock()
        listener = Mock()

        # test
        canceled = Mock()
        canceled.is_set.return_value = False
        batch = Batch(canceled, primary, sources, requests, listener)

        # validation
        self.assertEqual(batch._mutex, fake_lock())
        self.assertEqual(batch.canceled, canceled)
        self.assertEqual(batch.primary, primary)
        self.assertEqual(batch.sources, sources)
        self.assertEqual(batch.requests, requests)
        self.assertEqual(batch.listener, listener)
        self.assertEqual(batch.in_progress.canceled, canceled)
        self.assertEqual(len(batch.queues), 0)
        self.assertTrue(isinstance(batch.in_progress, Tracker))
        self.assertTrue(isinstance(batch.queues, dict))

    @patch('pulp.server.content.sources.container.RLock', Mock())
    def test_is_canceled(self):
        canceled = Mock()
        canceled.is_set.return_value = False
        batch = Batch(canceled, None, None, None, None)

        # test
        self.assertFalse(batch.is_canceled)
        canceled.is_set.return_value = True
        self.assertTrue(batch.is_canceled)

    @patch('pulp.server.content.sources.container.RLock', Mock())
    @patch('pulp.server.content.sources.container.Tracker.decrement')
    @patch('pulp.server.content.sources.container.Item')
    @patch('pulp.server.content.sources.container.Batch.find_queue')
    def test_dispatch(self, fake_find, fake_item, fake_decrement):
        fake_queue = Mock()
        fake_request = Mock()
        sources = [(Mock(), 'http://')]
        fake_request.sources = iter(sources)
        fake_find.return_value = fake_queue
        # test
        canceled = Mock()
        canceled.is_set.return_value = False
        batch = Batch(canceled, None, None, None, None)
        dispatched = batch.dispatch(fake_request)

        # validation
        fake_find.assert_called_with(sources[0][0])
        fake_item.assert_called_with(fake_request, sources[0][1])
        fake_queue.put.assert_called_with(fake_item())
        self.assertTrue(dispatched)
        self.assertFalse(fake_decrement.called)

    @patch('pulp.server.content.sources.container.RLock', Mock())
    @patch('pulp.server.content.sources.container.Batch.find_queue')
    @patch('pulp.server.content.sources.container.Tracker.decrement')
    def test_dispatch_no_remaining_sources(self, fake_decrement, fake_find):
        fake_queue = Mock()
        fake_request = Mock()
        sources = []
        fake_request.sources = iter(sources)
        fake_find.return_value = fake_queue

        # test
        canceled = Mock()
        canceled.is_set.return_value = False
        batch = Batch(canceled, None, None, None, None)
        dispatched = batch.dispatch(fake_request)

        # validation
        fake_decrement.assert_called_once_with()
        self.assertFalse(dispatched)
        self.assertFalse(fake_queue.put.called)
        self.assertFalse(fake_find.called)

    @patch('pulp.server.content.sources.container.RLock')
    @patch('pulp.server.content.sources.container.Batch._add_queue')
    def test_find_queue(self, fake_add, fake_lock):
        fake_source = Mock()
        fake_source.id = 'fake-id'
        fake_lock.__enter__ = Mock()
        fake_lock.__exit__ = Mock()

        # test
        canceled = Mock()
        canceled.is_set.return_value = False
        batch = Batch(canceled, None, None, None, None)
        batch.queues[fake_source.id] = Mock()
        queue = batch.find_queue(fake_source)

        # validation
        self.assertFalse(fake_add.called)
        self.assertEqual(queue, batch.queues[fake_source.id])

    @patch('pulp.server.content.sources.container.RLock')
    @patch('pulp.server.content.sources.container.Batch._add_queue')
    def test_find_queue_not_found(self, fake_add, fake_lock):
        fake_source = Mock()
        fake_source.id = 'fake-id'
        fake_lock.__enter__ = Mock()
        fake_lock.__exit__ = Mock()

        # test
        canceled = Mock()
        canceled.is_set.return_value = False
        batch = Batch(canceled, None, None, None, None)
        queue = batch.find_queue(fake_source)

        # validation
        fake_add.assert_called_with(fake_source)
        self.assertEqual(batch._mutex.__enter__.call_count, 1)
        self.assertEqual(batch._mutex.__exit__.call_count, 1)
        self.assertEqual(queue, fake_add())

    @patch('pulp.server.content.sources.container.RLock', Mock())
    @patch('pulp.server.content.sources.container.NectarListener')
    @patch('pulp.server.content.sources.container.RequestQueue')
    def test_add_queue(self, fake_queue, fake_listener):
        fake_source = Mock()
        fake_source.id = 'fake-id'
        fake_queue().downloader = Mock()

        # test
        canceled = Mock()
        canceled.is_set.return_value = False
        batch = Batch(canceled, None, None, None, None)
        queue = batch._add_queue(fake_source)

        # validation
        fake_queue.assert_called_with(canceled, fake_source)
        fake_listener.assert_called_with(batch)
        fake_queue().start.assert_called_with()
        self.assertEqual(fake_queue().downloader.event_listener, fake_listener())
        self.assertEqual(batch.queues[fake_source.id], fake_queue())
        self.assertEqual(queue, fake_queue())

    @patch('pulp.server.content.sources.container.Tracker.wait')
    @patch('pulp.server.content.sources.container.Batch.dispatch')
    def test_download(self, fake_dispatch, fake_wait):
        primary = Mock()
        sources = [Mock(), Mock()]
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
        canceled = Mock()
        canceled.is_set.return_value = False
        batch = Batch(canceled, primary, sources, iter(requests), None)
        batch.queues = {'source-1': queue_1, 'source-2': queue_2}  # simulated
        report = batch.download()

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

    @patch('pulp.server.content.sources.container.Tracker.wait')
    @patch('pulp.server.content.sources.container.Batch.dispatch')
    def test_download_nothing(self, fake_dispatch, fake_wait):
        primary = Mock()
        sources = []
        requests = []

        # test
        canceled = Mock()
        canceled.is_set.return_value = False
        batch = Batch(canceled, primary, sources, iter(requests), None)
        report = batch.download()

        # validation
        # initial dispatch
        self.assertFalse(fake_dispatch.called)
        self.assertTrue(isinstance(report, DownloadReport))
        self.assertEqual(len(report.downloads), 0)
        fake_wait.assert_called_once_with(0)

    @patch('pulp.server.content.sources.container.Tracker.wait')
    @patch('pulp.server.content.sources.container.Batch.dispatch')
    def test_download_canceled(self, fake_dispatch, fake_wait):
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
        canceled = Mock()
        canceled.is_set.return_value = True
        batch = Batch(canceled, None, [], [Mock()], None)
        batch.queues = {'source-1': queue_1, 'source-2': queue_2}  # simulated
        report = batch.download()

        # validation
        # initial dispatch
        self.assertFalse(fake_dispatch.called)
        # queue shutdown
        for queue in batch.queues.values():
            queue.put.assert_called_with(None)
            queue.halt.assert_called_with()
            queue.join.assert_called_with()
        # wait
        fake_wait.assert_called_once_with(0)
        # report
        self.assertTrue(isinstance(report, DownloadReport))
        self.assertEqual(len(report.downloads), 2)
        self.assertEqual(report.downloads['source-1'].total_succeeded, 100)
        self.assertEqual(report.downloads['source-1'].total_failed, 3)
        self.assertEqual(report.downloads['source-2'].total_succeeded, 200)
        self.assertEqual(report.downloads['source-2'].total_failed, 10)

    @patch('pulp.server.content.sources.container.Tracker.wait')
    @patch('pulp.server.content.sources.container.Batch.dispatch')
    def test_download_with_exception(self, fake_dispatch, fake_wait):
        primary = Mock()
        fake_dispatch.side_effect = ValueError()
        sources = [Mock(), Mock()]
        requests = [Mock(), Mock(), Mock()]

        # test
        canceled = Mock()
        canceled.is_set.return_value = False
        batch = Batch(canceled, primary, sources, iter(requests), None)
        batch.queues = {'source-1': Mock(), 'source-2': Mock()}  # simulated
        self.assertRaises(ValueError, batch.download)

        # validation
        fake_wait.assert_called_once_with(0)
        for queue in batch.queues.values():
            queue.put.assert_called_with(None)
            queue.halt.assert_called_with()
            queue.join.assert_called_with()


class TestRequestQueue(TestCase):

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Thread.setDaemon')
    @patch('pulp.server.content.sources.container.Queue')
    def test_construction(self, fake_queue, fake_setDaemon):
        source = Mock()
        source.id = 'fake_id'
        source.max_concurrent = 10

        # test
        canceled = Mock()
        canceled.is_set.return_value = False
        queue = RequestQueue(canceled, source)
        queue.setDaemon = Mock()

        # validation
        fake_queue.assert_called_with(source.max_concurrent)
        fake_setDaemon.assert_called_with(True)
        self.assertEqual(queue._halted, False)
        self.assertEqual(queue.canceled, canceled)
        self.assertEqual(queue.queue, fake_queue())
        self.assertEqual(queue.downloader, source.get_downloader())

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue', Mock())
    def test__run(self):
        canceled = Mock()
        canceled.is_set.return_value = False

        # test
        queue = RequestQueue(canceled, Mock())

        # validation
        # all good
        queue._halted = False
        canceled.is_set.return_value = False
        self.assertTrue(queue._run)
        # halted only
        queue._halted = True
        canceled.is_set.return_value = False
        self.assertFalse(queue._run)
        # canceled only
        queue._halted = False
        canceled.is_set.return_value = True
        self.assertFalse(queue._run)
        # both
        queue._halted = True
        canceled.is_set.return_value = True
        self.assertFalse(queue._run)

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue')
    def test_put(self, fake_queue):
        canceled = Mock()
        canceled.is_set.return_value = False

        # test
        item = Mock()
        queue = RequestQueue(canceled, Mock())
        queue.put(item)

        # validation
        fake_queue().put.assert_called_with(item, timeout=3)

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue')
    def test_put_canceled(self, fake_queue):
        canceled = Mock()
        canceled.is_set.return_value = False

        # test
        item = Mock()
        queue = RequestQueue(canceled, Mock())
        canceled.is_set.return_value = True
        queue.put(item)

        # validation
        self.assertFalse(fake_queue().put.called)

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue')
    def test_put_halted(self, fake_queue):
        canceled = Mock()
        canceled.is_set.return_value = False

        # test
        item = Mock()
        queue = RequestQueue(canceled, Mock())
        queue.halt()
        queue.put(item)

        # validation
        self.assertFalse(fake_queue().put.called)

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue')
    def test_put_full(self, fake_queue):
        canceled = Mock()
        canceled.is_set.return_value = False
        fake_queue().put.side_effect = SideEffect([Full(), Full(), None])

        # test
        item = Mock()
        queue = RequestQueue(canceled, Mock())
        queue.put(item)

        # validation
        self.assertEqual(fake_queue().put.call_count, 3)

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue')
    def test_get(self, fake_queue):
        canceled = Mock()
        canceled.is_set.return_value = False
        fake_queue().get.return_value = 123

        # test
        queue = RequestQueue(canceled, Mock())
        item = queue.get()

        # validation
        fake_queue().get.assert_called_with(timeout=3)
        self.assertEqual(item, 123)

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue')
    def test_get_canceled(self, fake_queue):
        canceled = Mock()
        canceled.is_set.return_value = False

        # test
        queue = RequestQueue(canceled, Mock())
        canceled.is_set.return_value = True
        item = queue.get()

        # validation
        self.assertFalse(fake_queue().get.called)
        self.assertEqual(item, None)

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue')
    def test_get_halted(self, fake_queue):
        canceled = Mock()
        canceled.is_set.return_value = False

        # test
        queue = RequestQueue(canceled, Mock())
        queue.halt()
        item = queue.get()

        # validation
        self.assertFalse(fake_queue().get.called)
        self.assertEqual(item, None)

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue')
    def test_get_empty(self, fake_queue):
        canceled = Mock()
        canceled.is_set.return_value = False
        fake_queue().get.side_effect = SideEffect([Empty(), Empty(), 123])

        # test
        queue = RequestQueue(canceled, Mock())
        item = queue.get()

        # validation
        self.assertEqual(fake_queue().get.call_count, 3)
        self.assertEqual(item, 123)

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue', Mock())
    @patch('pulp.server.content.sources.container.NectarFeed')
    def test_run(self, fake_feed):
        canceled = Mock()
        canceled.is_set.return_value = False

        # test
        queue = RequestQueue(canceled, Mock())
        queue.run()

        # validation
        queue.downloader.download.assert_called_with(fake_feed())

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue', Mock())
    @patch('pulp.server.content.sources.container.RequestQueue.drain')
    @patch('pulp.server.content.sources.container.NectarFeed')
    def test_run_with_exception(self, fake_feed, fake_drain):
        canceled = Mock()
        canceled.is_set.return_value = False

        # test
        queue = RequestQueue(canceled, Mock())
        queue.downloader.download.side_effect = ValueError()
        queue.run()

        # validation
        queue.downloader.download.assert_called_with(fake_feed())
        fake_drain.assert_called_with()

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue', Mock())
    @patch('pulp.server.content.sources.container.NectarDownloadReport.from_download_request')
    @patch('pulp.server.content.sources.container.NectarFeed')
    def test_drain(self, fake_feed, fake_from):
        canceled = Mock()
        canceled.is_set.return_value = False
        queued = [1, 2, 3]
        fake_feed.return_value = queued
        fake_from.side_effect = queued

        # test
        queue = RequestQueue(canceled, Mock())
        queue.drain()

        # validation
        calls = fake_from.call_args_list
        self.assertEqual(len(calls), len(queued))
        for i, request in enumerate(queued):
            self.assertEqual(calls[i][0][0], request)
        calls = queue.downloader.fire_download_failed.call_args_list
        for i, request in enumerate(queued):
            self.assertEqual(calls[i][0][0], request)

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue', Mock())
    def test_halt(self):
        canceled = Mock()
        canceled.is_set.return_value = False

        # test
        queue = RequestQueue(canceled, Mock())
        queue.halt()

        # validation
        self.assertTrue(queue._halted)


class TestNectarFeed(TestCase):

    def test_construction(self):
        queue = Mock()

        # test
        feed = NectarFeed(queue)

        # validation
        self.assertEqual(feed.queue, queue)

    @patch('pulp.server.content.sources.container.DownloadRequest')
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


class TestListener(TestCase):

    class MyListener(Listener):
        pass

    def test_declarations(self):
        listener = TestListener.MyListener()
        # validation
        self.assertTrue(inspect.ismethod(listener.download_started))
        self.assertTrue(inspect.ismethod(listener.download_succeeded))
        self.assertTrue(inspect.ismethod(listener.download_failed))


class TestTracker(TestCase):

    def test_construction(self):
        # test
        canceled = Mock()
        tracker = Tracker(canceled)

        # validation
        self.assertEqual(tracker.canceled, canceled)
        self.assertTrue(isinstance(tracker.queue, Queue))

    @patch('pulp.server.content.sources.container.Queue.put')
    def test_decrement(self, fake_put):
        # test
        tracker = Tracker(None)
        tracker.decrement()

        # validation
        fake_put.assert_called_once_with(0)

    @patch('pulp.server.content.sources.container.Queue.get')
    def test_wait(self, fake_get):
        events = [0, 0, 0]
        canceled = Mock()
        canceled.is_set.return_value = False
        fake_get.side_effect = events

        # test
        n = len(events)
        tracker = Tracker(canceled)
        tracker.wait(n)

        # validation
        self.assertEqual(canceled.is_set.call_count, n)
        self.assertEqual(fake_get.call_count, n)

    def test_wait_value_error(self):
        # test
        tracker = Tracker(None)
        self.assertRaises(ValueError, tracker.wait, -1)

    @patch('pulp.server.content.sources.container.Queue.get')
    def test_wait_raising_empty(self, fake_get):
        canceled = Mock()
        canceled.is_set.return_value = False
        tokens = [Empty(), 0, 0, 0]

        fake_get.side_effect = SideEffect(tokens)

        # test
        tracker = Tracker(canceled)
        tracker.wait(len(tokens) - 1)

        # validation
        self.assertEqual(canceled.is_set.call_count, len(tokens))
        self.assertEqual(fake_get.call_count, len(tokens))
