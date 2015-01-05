from base import PulpServerTests

from mock import patch, Mock

from pulp.server.managers import status as status_manager


class StatusManagerTests(PulpServerTests):

    @patch('pulp.server.managers.status.get_distribution')
    def test_get_version(self, mock_get_distribution):
        mock_distribution = Mock()
        mock_distribution.version = "1.2.3"
        mock_get_distribution.return_value = mock_distribution

        self.assertEquals(status_manager.get_version(), {'platform_version': '1.2.3'})

    @patch('pulp.server.managers.resources.filter_workers')
    def test_get_workers(self, mock_filter_workers):
        mock_filter_workers.return_value = [{"last_heartbeat": "123456", "name": "some_worker_1"},
                                            {"last_heartbeat": "123456", "name": "some_worker_2"}]

        self.assertEquals(status_manager.get_workers(), [{"last_heartbeat": "123456",
                                                          "name": "some_worker_1"},
                                                         {"last_heartbeat": "123456",
                                                          "name": "some_worker_2"}])

    @patch('pulp.server.async.celery_instance.celery')
    def test_get_broker_conn_status(self, mock_celery):
        mock_celery.connection = Mock()

        self.assertEquals(status_manager.get_broker_conn_status(), {'connected': True})

    @patch('pulp.server.db.connection.get_database')
    def test_get_mongo_conn_status(self, mock_get_database):
        self.assertEquals(status_manager.get_mongo_conn_status(), {'connected': True})

    @patch('pulp.server.async.celery_instance.celery.connection')
    def test_get_broker_conn_status_exception(self, mock_celery_conn):
        mock_conn = Mock()
        mock_conn.connect.side_effect = Exception("boom!")
        mock_celery_conn.return_value = mock_conn

        self.assertEquals(status_manager.get_broker_conn_status(), {'connected': False})

    @patch('pulp.server.db.connection.get_database')
    def test_get_mongo_conn_status_exception(self, mock_get_database):
        mock_get_database.side_effect = Exception("boom!")

        self.assertEquals(status_manager.get_mongo_conn_status(), {'connected': False})
