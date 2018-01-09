import unittest

import datetime
import mock

from pulp.server.async import worker_watcher


class TestHandleWorkerHeartbeat(unittest.TestCase):

    @mock.patch('pulp.server.async.worker_watcher.datetime')
    @mock.patch('pulp.server.async.worker_watcher._logger')
    @mock.patch('pulp.server.async.worker_watcher.Worker')
    def test_handle_worker_heartbeat_new(self, mock_worker, mock_logger, mock_datetime):
        """
        Ensure that we save a record and log when a new worker comes online.
        """
        mock_datetime.utcnow.return_value = datetime.datetime(2017, 1, 1, 1, 1, 1)
        mock_worker.objects.return_value.first.return_value = None
        worker_watcher.handle_worker_heartbeat('fake-worker')
        mock_logger.info.assert_called_once_with('New worker \'fake-worker\' discovered')
        mock_worker.objects.return_value.update_one.\
            assert_called_once_with(set__last_heartbeat=mock_datetime.utcnow(), upsert=True)

    @mock.patch('pulp.server.async.worker_watcher.datetime')
    @mock.patch('pulp.server.async.worker_watcher._logger')
    @mock.patch('pulp.server.async.worker_watcher.Worker')
    def test_handle_worker_heartbeat_update(self, mock_worker, mock_logger, mock_datetime):
        """
        Ensure that we don't log when an existing worker is updated.
        """
        mock_datetime.utcnow.return_value = datetime.datetime(2017, 1, 1, 1, 1, 1)
        mock_worker.objects.return_value.first.return_value = mock.Mock()
        worker_watcher.handle_worker_heartbeat('fake-worker')
        self.assertEquals(mock_logger.info.called, False)
        mock_worker.objects.return_value.update_one.\
            assert_called_once_with(set__last_heartbeat=mock_datetime.utcnow(), upsert=True)


class TestHandleWorkerOffline(unittest.TestCase):
    @mock.patch('pulp.server.async.worker_watcher._delete_worker')
    @mock.patch('pulp.server.async.worker_watcher._')
    @mock.patch('pulp.server.async.worker_watcher._logger')
    def test_handle_worker_offline(self, mock__logger, mock_gettext, mock__delete_worker):
        """
        Ensure that we log and clean up appropriately when the worker goes offline.
        """
        worker_watcher.handle_worker_offline('fake-worker')
        mock_gettext.assert_called_once_with("Worker '%s' shutdown")
        mock__logger.info.assert_called_once()
        mock__delete_worker.assert_called_once_with('fake-worker', normal_shutdown=True)
