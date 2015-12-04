import datetime
import unittest

import mock

from pulp.server.async import worker_watcher


class TestParseAndLogEvent(unittest.TestCase):
    def test__parse_and_log_event(self):
        event = {'timestamp': 1449260644.097711, 'local_received': 1449260669.830475,
                 'type': 'fake-type', 'hostname': 'fake-worker'}

        result = worker_watcher._parse_and_log_event(event)

        # assert that the values in the result dictionary are right
        self.assertEqual(result['timestamp'], datetime.datetime.utcfromtimestamp(1449260644.097711))
        self.assertEqual(result['local_received'],
                         datetime.datetime.utcfromtimestamp(1449260669.830475))
        self.assertTrue(result['type'] is event['type'])
        self.assertTrue(result['worker_name'] is event['hostname'])

    @mock.patch('pulp.server.async.worker_watcher._logger')
    @mock.patch('pulp.server.async.worker_watcher._')
    def test__log_event_logs_correctly(self, mock_gettext, mock__logger):
        event_info = {'timestamp': 1449260644.097711, 'local_received': 1449260669.830475,
                      'type': 'fake-type', 'hostname': 'fake-worker'}

        worker_watcher._parse_and_log_event(event_info)

        log_string = ("'%(type)s' sent at time %(timestamp)s from %(worker_name)s, received at "
                      "time: %(local_received)s")
        mock_gettext.assert_called_with(log_string)
        mock__logger.assert_called_once()


class TestHandleWorkerHeartbeat(unittest.TestCase):

    @mock.patch('pulp.server.async.worker_watcher._logger')
    @mock.patch('pulp.server.async.worker_watcher.Worker')
    @mock.patch('pulp.server.async.worker_watcher._parse_and_log_event')
    def test_handle_worker_heartbeat_new(self, mock__parse_and_log_event,
                                         mock_worker, mock_logger):
        """
        Ensure that we save a record and log when a new worker comes online.
        """

        mock_event = mock.Mock()
        mock_worker.objects.return_value.first.return_value = None
        mock__parse_and_log_event.return_value = {
            'worker_name': 'fake-worker', 'timestamp': '2014-12-08T15:52:29Z',
            'local_received': '2014-12-08T15:52:36Z', 'type': 'fake-type'}

        worker_watcher.handle_worker_heartbeat(mock_event)

        mock_worker.objects.return_value.update_one.\
            assert_called_once_with(set__last_heartbeat='2014-12-08T15:52:36Z', upsert=True)
        mock_logger.info.assert_called_once_with('New worker \'fake-worker\' discovered')

    @mock.patch('pulp.server.async.worker_watcher._logger')
    @mock.patch('pulp.server.async.worker_watcher.Worker')
    @mock.patch('pulp.server.async.worker_watcher._parse_and_log_event')
    def test_handle_worker_heartbeat_update(self, mock__parse_and_log_event,
                                            mock_worker, mock_logger):
        """
        Ensure that we save a record but don't log when an existing worker is updated.
        """

        mock_event = mock.Mock()
        mock_worker.objects.return_value.first.return_value = mock.Mock()
        mock__parse_and_log_event.return_value = {
            'worker_name': 'fake-worker', 'timestamp': '2014-12-08T15:52:29Z',
            'local_received': '2014-12-08T15:52:48Z', 'type': 'fake-type'}

        worker_watcher.handle_worker_heartbeat(mock_event)

        mock_worker.objects.return_value.update_one.\
            assert_called_once_with(set__last_heartbeat='2014-12-08T15:52:48Z', upsert=True)
        self.assertEquals(mock_logger.info.called, False)


class TestHandleWorkerOffline(unittest.TestCase):
    @mock.patch('pulp.server.async.worker_watcher._parse_and_log_event')
    @mock.patch('pulp.server.async.worker_watcher._delete_worker')
    @mock.patch('pulp.server.async.worker_watcher._')
    @mock.patch('pulp.server.async.worker_watcher._logger')
    def test_handle_worker_offline(self, mock__logger, mock_gettext, mock__delete_worker,
                                   mock__parse_and_log_event):
        mock_event = mock.Mock()

        worker_watcher.handle_worker_offline(mock_event)

        event_info = mock__parse_and_log_event.return_value
        mock__parse_and_log_event.assert_called_once_with(mock_event)
        mock_gettext.assert_called_once_with("Worker '%(worker_name)s' shutdown")
        mock__logger.info.assert_called_once()
        mock__delete_worker.assert_called_once_with(event_info['worker_name'], normal_shutdown=True)
