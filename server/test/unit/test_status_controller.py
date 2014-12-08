from base import PulpWebserviceTests

from mock import Mock, patch


class StatusControllerTests(PulpWebserviceTests):

    def test_get(self):
        status, body = self.get('/v2/status/')

        self.assertEqual(status, 200)
        # test for deprecated api_version field
        self.assertTrue('api_version' in body)
        self.assertTrue('versions' in body)

    @patch("pulp.server.webservices.controllers.status.status_manager")
    def test_get_worker_list(self, mock_status_manager):
        mock_status_manager.get_version.return_value = {"platform_version": "1.2.3"}
        mock_status_manager.get_broker_conn_status.return_value = {'connected': True}
        mock_status_manager.get_mongo_conn_status.return_value = {'connected': True}
        mock_status_manager.get_workers.return_value = [
            {
                "last_heartbeat": "2014-12-08T15:52:29Z",
                "name": "reserved_resource_worker-0@fake.hostname"
            },
            {
                "last_heartbeat": "2014-12-08T15:52:29Z",
                "name": "resource_manager@fake.hostname"
            }]

        status, body = self.get('/v2/status/')

        for w in body['known_workers']:
            self.assertEquals(w['last_heartbeat'], '2014-12-08T15:52:29Z')
            self.assertTrue(w['name'].endswith('@fake.hostname'))

    @patch("pulp.server.webservices.controllers.status.status_manager")
    def test_get_worker_list_no_db(self, mock_status_manager):
        mock_status_manager.get_version.return_value = {"platform_version": "1.2.3"}
        mock_status_manager.get_broker_conn_status.return_value = {'connected': True}
        mock_status_manager.get_mongo_conn_status.return_value = {'connected': False}

        status, body = self.get('/v2/status/')

        self.assertEquals(body['known_workers'], [])
        self.assertEquals(body['database_connection'], {'connected': False})
        # make sure we don't attempt to get the worker list if the DB is not available
        self.assertEquals(mock_status_manager.get_workers.called, False)

    @patch("pulp.server.webservices.controllers.status.status_manager")
    def test_get_broker_conn_status(self, mock_status_manager):
        mock_status_manager.get_version.return_value = {"platform_version": "1.2.3"}
        mock_status_manager.get_broker_conn_status.return_value = {'connected': False}
        mock_status_manager.get_mongo_conn_status.return_value = {'connected': True}

        status, body = self.get('/v2/status/')

        self.assertEquals(body['messaging_connection'], {'connected': False})
