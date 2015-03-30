import unittest

import mock

from pulp.server.webservices.views.status import StatusView


class TestStatusView(unittest.TestCase):
    """
    Test pulp server status view.
    """

    @mock.patch('pulp.server.webservices.views.status.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.status.status_manager')
    def test_get_server_status(self, mock_status, mock_resp):
        """
        Test server status
        """
        mock_status.get_version.return_value = {"platform_version": '2.6.1'}
        mock_status.get_mongo_conn_status.return_value = {'connected': True}
        mock_status.get_broker_conn_status.return_value = {'connected': True}
        mock_worker = mock.MagicMock()
        mock_worker.to_mongo.return_value.to_dict.return_value = {
            "last_heartbeat": "2015-03-19T13:55:36Z",
            "name": "reserved_resource_worker-0@example.com"}
        mock_status.get_workers.return_value = [mock_worker]

        request = mock.MagicMock()
        status = StatusView()
        response = status.get(request)
        expected_cont = {'known_workers': [{'last_heartbeat': '2015-03-19T13:55:36Z',
                                            'name': 'reserved_resource_worker-0@example.com'}],
                         'messaging_connection': {'connected': True},
                         'database_connection': {'connected': True},
                         'api_version': '2',
                         'versions': {"platform_version": '2.6.1'}}
        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.status.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.status.status_manager')
    def test_get_server_status_no_db_conn(self, mock_status, mock_resp):
        """
        Test server status woth no connection to db
        """
        mock_status.get_version.return_value = {"platform_version": '2.6.1'}
        mock_status.get_mongo_conn_status.return_value = {'connected': False}
        mock_status.get_broker_conn_status.return_value = {'connected': True}

        request = mock.MagicMock()
        status = StatusView()
        response = status.get(request)
        expected_cont = {'known_workers': [],
                         'messaging_connection': {'connected': True},
                         'database_connection': {'connected': False},
                         'api_version': '2',
                         'versions': {"platform_version": '2.6.1'}}
        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)

    @mock.patch('pulp.server.webservices.views.status.generate_json_response_with_pulp_encoder')
    @mock.patch('pulp.server.webservices.views.status.status_manager')
    def test_get_server_status_broker_conn(self, mock_status, mock_resp):
        """
        Test server status with broker connection false.
        """
        mock_status.get_version.return_value = {"platform_version": '2.6.1'}
        mock_status.get_mongo_conn_status.return_value = {'connected': True}
        mock_status.get_broker_conn_status.return_value = {'connected': False}
        mock_worker = mock.MagicMock()
        mock_worker.to_mongo.return_value.to_dict.return_value = {
            "last_heartbeat": "2015-03-19T13:55:36Z",
            "name": "reserved_resource_worker-0@example.com"}
        mock_status.get_workers.return_value = [mock_worker]

        request = mock.MagicMock()
        status = StatusView()
        response = status.get(request)
        expected_cont = {'known_workers': [{'last_heartbeat': '2015-03-19T13:55:36Z',
                                            'name': 'reserved_resource_worker-0@example.com'}],
                         'messaging_connection': {'connected': False},
                         'database_connection': {'connected': True},
                         'api_version': '2',
                         'versions': {"platform_version": '2.6.1'}}
        mock_resp.assert_called_once_with(expected_cont)
        self.assertTrue(response is mock_resp.return_value)
