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

from Queue import Full, Empty
from collections import namedtuple

from mock import patch, Mock

from pulp.server.content.sources.container import (
    ContentContainer, NectarListener, Item, RequestQueue, Batch, DownloadReport, Listener)
from pulp.server.content.sources.model import ContentSource


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
        canceled = FakeEvent()
        downloader = Mock()
        requests = Mock()
        listener = Mock()

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
        for n in range(3):
            s = ContentSource('s-%d' % n, {})
            s.refresh = Mock(return_value=[n])
            s.get_downloader = Mock()
            sources[s.id] = s

        fake_manager().has_entries.return_value = False
        fake_load.return_value = sources

        # test
        canceled = FakeEvent()
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
            s.get_downloader = Mock()
            sources[s.id] = s

        fake_manager().has_entries.return_value = False
        fake_load.return_value = sources

        # test
        canceled = FakeEvent()
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
        canceled = FakeEvent()
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
        canceled = FakeEvent()
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
        batch.listener = Mock()
        report = Mock()
        report.data = Mock()

        # test
        listener = NectarListener(batch)
        listener.download_succeeded(report)

        # validation
        batch.finished.assert_called_with(report.data)
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
        batch.finished.assert_called_with(report.data)
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
        canceled = FakeEvent()
        primary = Mock()
        sources = Mock()
        requests = Mock()
        listener = Mock()

        # test
        batch = Batch(canceled, primary, sources, requests, listener)

        # validation
        self.assertEqual(batch._mutex, fake_lock())
        self.assertEqual(batch.canceled, canceled)
        self.assertEqual(batch.primary, primary)
        self.assertEqual(batch.sources, sources)
        self.assertEqual(batch.requests, requests)
        self.assertEqual(batch.listener, listener)
        self.assertEqual(len(batch.in_progress), 0)
        self.assertEqual(len(batch.queues), 0)
        self.assertTrue(isinstance(batch.in_progress, set))
        self.assertTrue(isinstance(batch.queues, dict))

    @patch('pulp.server.content.sources.container.RLock', Mock())
    def test_is_canceled(self):
        canceled = FakeEvent()
        batch = Batch(canceled, None, None, None, None)

        # test
        self.assertFalse(batch.is_canceled)
        canceled.set()
        self.assertTrue(batch.is_canceled)

    @patch('pulp.server.content.sources.container.RLock', Mock())
    @patch('pulp.server.content.sources.container.Item')
    @patch('pulp.server.content.sources.container.Batch.find_queue')
    def test_dispatch(self, fake_find, fake_item):
        canceled = FakeEvent()
        fake_queue = Mock()
        fake_request = Mock()
        sources = [(Mock(), 'http://')]
        fake_request.sources = iter(sources)
        fake_find.return_value = fake_queue

        # test
        batch = Batch(canceled, None, None, None, None)
        dispatched = batch.dispatch(fake_request)

        # validation
        fake_find.assert_called_with(sources[0][0])
        fake_item.assert_called_with(fake_request, sources[0][1])
        fake_queue.put.assert_called_with(fake_item())
        self.assertTrue(dispatched)

    @patch('pulp.server.content.sources.container.RLock', Mock())
    @patch('pulp.server.content.sources.container.Batch.find_queue')
    @patch('pulp.server.content.sources.container.Batch.finished')
    def test_dispatch_no_remaining_sources(self, fake_finished, fake_find):
        canceled = FakeEvent()
        fake_queue = Mock()
        fake_request = Mock()
        sources = []
        fake_request.sources = iter(sources)
        fake_find.return_value = fake_queue

        # test
        batch = Batch(canceled, None, None, None, None)
        dispatched = batch.dispatch(fake_request)

        # validation
        fake_finished.assert_called_with(fake_request)
        self.assertFalse(dispatched)
        self.assertFalse(fake_queue.put.called)
        self.assertFalse(fake_find.called)

    @patch('pulp.server.content.sources.container.RLock', Mock())
    @patch('pulp.server.content.sources.container.Batch._add_queue')
    def test_find_queue(self, fake_add):
        canceled = FakeEvent()
        fake_source = Mock()
        fake_source.id = 'fake-id'

        # test
        batch = Batch(canceled, None, None, None, None)
        batch.queues[fake_source.id] = Mock()
        queue = batch.find_queue(fake_source)

        # validation
        self.assertFalse(fake_add.called)
        self.assertEqual(queue, batch.queues[fake_source.id])

    @patch('pulp.server.content.sources.container.RLock')
    @patch('pulp.server.content.sources.container.Batch._add_queue')
    def test_find_queue_not_found(self, fake_add, fake_lock):
        canceled = FakeEvent()
        fake_source = Mock()
        fake_source.id = 'fake-id'

        # test
        batch = Batch(canceled, None, None, None, None)
        queue = batch.find_queue(fake_source)

        # validation
        fake_add.assert_called_with(fake_source)
        fake_lock().acquire.assert_called_once_with()
        fake_lock().release.assert_called_once_with()
        self.assertEqual(queue, fake_add())

    @patch('pulp.server.content.sources.container.RLock', Mock())
    @patch('pulp.server.content.sources.container.NectarListener')
    @patch('pulp.server.content.sources.container.RequestQueue')
    def test_add_queue(self, fake_queue, fake_listener):
        canceled = FakeEvent()
        fake_source = Mock()
        fake_source.id = 'fake-id'
        fake_queue().downloader = Mock()

        # test
        batch = Batch(canceled, None, None, None, None)
        queue = batch._add_queue(fake_source)

        # validation
        fake_queue.assert_called_with(canceled, fake_source)
        fake_listener.assert_called_with(batch)
        fake_queue().start.assert_called_with()
        self.assertEqual(fake_queue().downloader.event_listener, fake_listener())
        self.assertEqual(batch.queues[fake_source.id], fake_queue())
        self.assertEqual(queue, fake_queue())

    @patch('pulp.server.content.sources.container.RLock', Mock())
    @patch('pulp.server.content.sources.container.sleep')
    @patch('pulp.server.content.sources.container.Batch.started')
    @patch('pulp.server.content.sources.container.Batch.is_waiting')
    @patch('pulp.server.content.sources.container.Batch.dispatch')
    def test_download(self, fake_dispatch, fake_waiting, fake_started, fake_sleep):
        primary = Mock()
        canceled = FakeEvent()
        fake_waiting.side_effect = [True, True, False]
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
        # started
        calls = fake_started.call_args_list
        self.assertEqual(len(calls), len(requests))
        for i, request in enumerate(requests):
            self.assertEqual(calls[i][0][0], requests[i])
        # waiting for completion
        self.assertEqual(fake_waiting.call_count, 3)
        self.assertEqual(fake_sleep.call_count, 2)
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

    @patch('pulp.server.content.sources.container.RLock', Mock())
    @patch('pulp.server.content.sources.container.Batch.started')
    @patch('pulp.server.content.sources.container.Batch.is_waiting')
    @patch('pulp.server.content.sources.container.Batch.dispatch')
    def test_download_nothing(self, fake_dispatch, fake_waiting, fake_started):
        primary = Mock()
        canceled = FakeEvent()
        fake_waiting.return_value = False
        sources = []
        requests = []

        # test
        batch = Batch(canceled, primary, sources, iter(requests), None)
        report = batch.download()

        # validation
        # initial dispatch
        self.assertFalse(fake_dispatch.called)
        self.assertFalse(fake_started.called)
        self.assertTrue(isinstance(report, DownloadReport))
        self.assertEqual(len(report.downloads), 0)
        fake_waiting.assert_called_once_with()

    @patch('pulp.server.content.sources.container.RLock', Mock())
    @patch('pulp.server.content.sources.container.Batch.started')
    @patch('pulp.server.content.sources.container.Batch.is_waiting')
    @patch('pulp.server.content.sources.container.Batch.dispatch')
    def test_download_canceled(self, fake_dispatch, fake_waiting, fake_started):
        canceled = FakeEvent()
        fake_waiting.return_value = False

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
        canceled.set()
        batch = Batch(canceled, None, [], [Mock()], None)
        batch.queues = {'source-1': queue_1, 'source-2': queue_2}  # simulated
        report = batch.download()

        # validation
        # initial dispatch
        self.assertFalse(fake_dispatch.called)
        self.assertFalse(fake_started.called)
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

    @patch('pulp.server.content.sources.container.RLock', Mock())
    @patch('pulp.server.content.sources.container.Batch.is_waiting')
    @patch('pulp.server.content.sources.container.Batch.dispatch')
    def test_download_with_exception(self, fake_dispatch, fake_waiting):
        primary = Mock()
        canceled = FakeEvent()
        fake_waiting.return_value = False
        fake_dispatch.side_effect = ValueError()
        sources = [Mock(), Mock()]
        requests = [Mock(), Mock(), Mock()]

        # test
        batch = Batch(canceled, primary, sources, iter(requests), None)
        batch.queues = {'source-1': Mock(), 'source-2': Mock()}  # simulated
        self.assertRaises(ValueError, batch.download)

        # validation
        self.assertEqual(fake_waiting.call_count, 1)
        for queue in batch.queues.values():
            queue.put.assert_called_with(None)
            queue.halt.assert_called_with()
            queue.join.assert_called_with()

    @patch('pulp.server.content.sources.container.RLock', Mock())
    def test_started(self):
        request = Mock()

        # test
        batch = Batch(None, None, None, None, None)
        batch.started(request)

        # validation
        self.assertTrue(request in batch.in_progress)
        self.assertEqual(len(batch.in_progress), 1)

    @patch('pulp.server.content.sources.container.RLock', Mock())
    def test_finished(self):
        request = Mock()

        # test
        batch = Batch(None, None, None, None, None)
        batch.in_progress.add(request)
        batch.finished(request)

        # validation
        self.assertFalse(request in batch.in_progress)
        self.assertEqual(len(batch.in_progress), 0)

    @patch('pulp.server.content.sources.container.RLock', Mock())
    def test_is_waiting(self):
        canceled = FakeEvent()
        request = Mock()

        # test
        batch = Batch(canceled, None, None, None, None)

        # 1 in-progress
        canceled._set = False
        batch.in_progress = {1}
        self.assertTrue(batch.is_waiting())
        # 1 in-progress but canceled
        canceled._set = True
        batch.in_progress = {1}
        self.assertFalse(batch.is_waiting())
        # 0 in-progress
        canceled._set = False
        batch.in_progress = set()
        self.assertFalse(batch.is_waiting())
        # 0 in-progress and canceled
        canceled._set = True
        batch.in_progress = set()
        self.assertFalse(batch.is_waiting())


class TestRequestQueue(TestCase):

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Thread.setDaemon')
    @patch('pulp.server.content.sources.container.Queue')
    def test_construction(self, fake_queue, fake_setDaemon):
        canceled = Mock()
        source = Mock()
        source.id = 'fake_id'
        source.max_concurrent = 10

        # test
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
        canceled = FakeEvent()

        # test
        queue = RequestQueue(canceled, Mock())

        # validation
        # all good
        queue._halted = False
        canceled._set = False
        self.assertTrue(queue._run)
        # halted only
        queue._halted = True
        canceled._set = False
        self.assertFalse(queue._run)
        # canceled only
        queue._halted = False
        canceled._set = True
        self.assertFalse(queue._run)
        # both
        queue._halted = True
        canceled._set = True
        self.assertFalse(queue._run)


    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue')
    def test_put(self, fake_queue):
        canceled = FakeEvent()

        # test
        item = Mock()
        queue = RequestQueue(canceled, Mock())
        queue.put(item)

        # validation
        fake_queue().put.assert_called_with(item, timeout=10)

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue')
    def test_put_canceled(self, fake_queue):
        canceled = FakeEvent()

        # test
        item = Mock()
        queue = RequestQueue(canceled, Mock())
        canceled.set()
        queue.put(item)

        # validation
        self.assertFalse(fake_queue().put.called)

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue')
    def test_put_halted(self, fake_queue):
        canceled = FakeEvent()

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
        canceled = FakeEvent()
        fake_queue().put.side_effect = [Full(), Full(), None]

        # test
        item = Mock()
        queue = RequestQueue(canceled, Mock())
        queue.put(item)

        # validation
        self.assertEqual(fake_queue().put.call_count, 3)

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue')
    def test_get(self, fake_queue):
        canceled = FakeEvent()
        fake_queue().get.return_value = 123

        # test
        queue = RequestQueue(canceled, Mock())
        item = queue.get()

        # validation
        fake_queue().get.assert_called_with(timeout=10)
        self.assertEqual(item, 123)

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue')
    def test_get_canceled(self, fake_queue):
        canceled = FakeEvent()

        # test
        queue = RequestQueue(canceled, Mock())
        canceled.set()
        queue.get()

        # validation
        self.assertFalse(fake_queue().get.called)

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue')
    def test_get_halted(self, fake_queue):
        canceled = FakeEvent()

        # test
        queue = RequestQueue(canceled, Mock())
        queue.halt()
        queue.get()

        # validation
        self.assertFalse(fake_queue().get.called)

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue')
    def test_get_empty(self, fake_queue):
        canceled = FakeEvent()
        fake_queue().get.side_effect = [Empty(), Empty(), 123]

        # test
        item = Mock()
        queue = RequestQueue(canceled, Mock())
        item = queue.get()

        # validation
        self.assertEqual(fake_queue().get.call_count, 3)
        self.assertEqual(item, 123)

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue', Mock())
    @patch('pulp.server.content.sources.container.RequestQueue.get')
    @patch('pulp.server.content.sources.container.DownloadRequest')
    def test_next(self, fake_request, fake_get):
        canceled = FakeEvent()
        req = namedtuple('Request', ['destination'])
        queued = [
            Item(req(1), 2),
            Item(req(3), 4),
            Item(req(5), 6)
        ]
        fake_get.side_effect = queued
        fake_request.side_effect = [1, 2, 3]

        # test
        queue = RequestQueue(canceled, Mock())
        fetched = list(queue.next())

        # validation
        fake_get.assert_called_with()
        calls = fake_request.call_args_list
        self.assertEqual(len(calls), 3)
        for i, item in enumerate(queued):
            self.assertEqual(calls[i][0][0], item.url)
            self.assertEqual(calls[i][0][1], item.request.destination)
            self.assertEqual(calls[i][1], dict(data=item.request))
        self.assertEqual(fetched, [1, 2, 3])

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue', Mock())
    @patch('pulp.server.content.sources.container.RequestQueue.get')
    @patch('pulp.server.content.sources.container.DownloadRequest')
    def test_next_end_of_queue(self, fake_request, fake_get):
        canceled = FakeEvent()
        req = namedtuple('Request', ['destination'])
        queued = [
            Item(req(1), 2),
            Item(req(3), 4),
            None  # end-of-queue
        ]
        fake_get.side_effect = queued
        fake_request.side_effect = [1, 2, 3]

        # test
        queue = RequestQueue(canceled, Mock())
        fetched = list(queue.next())

        # validation
        fake_get.assert_called_with()
        calls = fake_request.call_args_list
        self.assertEqual(len(calls), 2)
        for i, item in enumerate(queued[:-1]):
            self.assertEqual(calls[i][0][0], item.url)
            self.assertEqual(calls[i][0][1], item.request.destination)
            self.assertEqual(calls[i][1], dict(data=item.request))
        self.assertEqual(fetched, [1, 2])

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue', Mock())
    @patch('pulp.server.content.sources.container.RequestQueue.get')
    @patch('pulp.server.content.sources.container.DownloadRequest')
    def test_next_canceled(self, fake_request, fake_get):
        canceled = FakeEvent()

        # test
        queue = RequestQueue(canceled, Mock())
        canceled.set()
        fetched = list(queue.next())

        # validation
        self.assertFalse(fake_get.called)
        self.assertFalse(fake_request.called)
        self.assertEqual(fetched, [])

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue', Mock())
    @patch('pulp.server.content.sources.container.RequestQueue.get')
    @patch('pulp.server.content.sources.container.DownloadRequest')
    def test_next_halted(self, fake_request, fake_get):
        canceled = FakeEvent()

        # test
        queue = RequestQueue(canceled, Mock())
        queue.halt()
        fetched = list(queue.next())

        # validation
        self.assertFalse(fake_get.called)
        self.assertFalse(fake_request.called)
        self.assertEqual(fetched, [])

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue', Mock())
    @patch('pulp.server.content.sources.container.RequestQueue.next')
    def test_run(self, fake_next):
        canceled = FakeEvent()

        # test
        queue = RequestQueue(canceled, Mock())
        queue.run()

        # validation
        queue.downloader.download.assert_called_with(fake_next())

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue', Mock())
    @patch('pulp.server.content.sources.container.RequestQueue.drain')
    @patch('pulp.server.content.sources.container.RequestQueue.next')
    def test_run_with_exception(self, fake_next, fake_drain):
        canceled = FakeEvent()

        # test
        queue = RequestQueue(canceled, Mock())
        queue.downloader.download.side_effect = ValueError()
        queue.run()

        # validation
        queue.downloader.download.assert_called_with(fake_next())
        fake_drain.assert_called_with()

    @patch('pulp.server.content.sources.container.Thread', new=Mock())
    @patch('pulp.server.content.sources.container.Queue', Mock())
    @patch('pulp.server.content.sources.container.NectarDownloadReport.from_download_request')
    @patch('pulp.server.content.sources.container.RequestQueue.next')
    def test_drain(self, fake_next, fake_from):
        canceled = FakeEvent()
        queued = [1, 2, 3]
        fake_next.return_value = queued
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
        canceled = FakeEvent()

        # test
        queue = RequestQueue(canceled, Mock())
        queue.halt()

        # validation
        self.assertTrue(queue._halted)


class TestListener(TestCase):

    class MyListener(Listener):
        pass

    def test_declarations(self):
        listener = TestListener.MyListener()
        # validation
        self.assertTrue(inspect.ismethod(listener.download_started))
        self.assertTrue(inspect.ismethod(listener.download_succeeded))
        self.assertTrue(inspect.ismethod(listener.download_failed))


# using this so nobody thinks the tests are using threads.


class FakeEvent(object):

    def __init__(self):
        self._set = False

    def isSet(self):
        return self._set

    def set(self):
        self._set = True