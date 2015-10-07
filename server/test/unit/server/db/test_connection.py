import unittest

from mock import call, patch, MagicMock, Mock
from pymongo.errors import AutoReconnect
import unittest2

from pulp.common import error_codes

from pulp.server import config
from pulp.server.db import connection
from pulp.server.exceptions import PulpCodedException


MONGO_MIN_TEST_VERSION = "2.4.0"


class MongoEngineConnectionError(Exception):
    pass


class TestDatabaseSeeds(unittest2.TestCase):

    def tearDown(self):
        # Reload the configuration so that things are cleaned up properly
        config.load_configuration()
        super(TestDatabaseSeeds, self).tearDown()

    def test_seeds_default(self):
        self.assertEqual(config._default_values['database']['seeds'], 'localhost:27017')

    @patch('pulp.server.db.connection.mongoengine')
    def test_seeds_invalid(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        config.config.set('database', 'replica_set', '')
        connection.initialize(seeds='localhost:27017:1234')
        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        database = config.config.get('database', 'name')
        mock_mongoengine.connect.assert_called_once_with(database, max_pool_size=max_pool_size,
                                                         host='localhost:27017:1234', replicaSet='')

    @patch('pulp.server.db.connection.mongoengine')
    def test_seeds_is_empty(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        config.config.set('database', 'replica_set', '')
        config.config.set('database', 'seeds', '')
        self.assertRaises(PulpCodedException, connection.initialize)

    @patch('pulp.server.db.connection.mongoengine')
    @patch('pulp.server.db.connection._connect_to_one_of_seeds')
    def test_seeds_is_set_from_argument(self, mock_connect_seeds, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        mock_connect_seeds.return_value.server_info.return_value = {'version': '2.6.0'}
        replica_set = 'fakeReplica'
        config.config.set('database', 'replica_set', replica_set)
        connection.initialize(seeds='firsthost:1234,secondhost:5678')
        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        database = config.config.get('database', 'name')
        mock_connect_seeds.assert_called_with({'max_pool_size': max_pool_size,
                                               'replicaSet': replica_set}, ['firsthost:1234',
                                                                            'secondhost:5678'],
                                              database)

    @patch('pulp.server.db.connection.mongoengine')
    @patch('pulp.server.db.connection._connect_to_one_of_seeds')
    def test_seeds_from_config(self, mock_connect_seeds, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        mock_connect_seeds.return_value.server_info.return_value = {'version': '2.6.0'}
        seeds = "firsthost:1234,secondhost:5678"
        replica_set = 'fakeReplica'
        config.config.set('database', 'seeds', seeds)
        config.config.set('database', 'replica_set', replica_set)

        connection.initialize()
        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        database = config.config.get('database', 'name')
        mock_connect_seeds.assert_called_with({'max_pool_size': max_pool_size,
                                               'replicaSet': replica_set}, ['firsthost:1234',
                                                                            'secondhost:5678'],
                                              database)

    @patch('pulp.server.db.connection.mongoengine')
    @patch('pulp.server.db.connection._connect_to_one_of_seeds')
    def test_multiple_seeds_no_replica_set(self, mock_connect_seeds, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        mock_connect_seeds.return_value.server_info.return_value = {'version': '2.6.0'}
        seeds = "firsthost:1234,secondhost:5678"
        config.config.set('database', 'write_concern', 'majority')
        config.config.set('database', 'seeds', seeds)
        with self.assertRaises(PulpCodedException) as connection_error:
            connection.initialize()
        self.assertEqual(connection_error.exception.error_code.message, error_codes.PLP0041.message)

    @patch('pulp.server.db.connection.mongoengine')
    @patch('pulp.server.db.connection._connect_to_one_of_seeds')
    def test_invalid_write_concern(self, mock_connect_seeds, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        mock_connect_seeds.return_value.server_info.return_value = {'version': '2.6.0'}
        seeds = "firsthost:1234,secondhost:5678"
        replica_set = 'fakeReplica'
        config.config.set('database', 'write_concern', 'blah')
        config.config.set('database', 'seeds', seeds)
        config.config.set('database', 'replica_set', replica_set)
        with self.assertRaises(PulpCodedException) as connection_error:
            connection.initialize()
        self.assertEqual(connection_error.exception.error_code.message, error_codes.PLP0043.message)


class TestDatabaseName(unittest.TestCase):

    def tearDown(self):
        # Reload the configuration so that things are cleaned up properly
        config.load_configuration()
        super(TestDatabaseName, self).tearDown()

    @patch('pulp.server.db.connection.mongoengine')
    def test__DATABASE_uses_default_name(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        host = 'champs.example.com:27018'
        replica_set = ''
        config.config.set('database', 'seeds', host)
        config.config.set('database', 'replica_set', replica_set)

        connection.initialize()

        name = config.config.get('database', 'name')
        mock_mongoengine.connect.assert_called_once_with(name, host=host, max_pool_size=10,
                                                         replicaSet=replica_set)

    @patch('pulp.server.db.connection.mongoengine')
    def test_name_is_set_from_argument(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        name = 'name_set_from_argument'
        host = 'champs.example.com:27018'
        replica_set = ''
        config.config.set('database', 'seeds', host)
        config.config.set('database', 'replica_set', replica_set)

        connection.initialize(name=name)

        mock_mongoengine.connect.assert_called_once_with(name, host=host, max_pool_size=10,
                                                         replicaSet=replica_set)


class TestDatabaseReplicaSet(unittest.TestCase):

    def tearDown(self):
        # Reload the configuration so that things are cleaned up properly
        config.load_configuration()
        super(TestDatabaseReplicaSet, self).tearDown()

    @patch('pulp.server.db.connection.mongoengine')
    def test_database_sets_replica_set(self, mock_mongoengine):
        mock_replica_set = Mock()
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        host = 'champs.example.com:27018'
        replica_set = ''
        config.config.set('database', 'seeds', host)
        config.config.set('database', 'replica_set', replica_set)
        connection.initialize(replica_set=mock_replica_set)

        database = config.config.get('database', 'name')

        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        mock_mongoengine.connect.assert_called_once_with(
            database, host=host, max_pool_size=max_pool_size,
            replicaSet=mock_replica_set)

    @patch('pulp.server.db.connection.mongoengine')
    def test_database_replica_set_from_config(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        config.config.set('database', 'replica_set', 'real_replica_set')
        config.config.set('database', 'name', 'nbachamps')
        config.config.set('database', 'seeds', 'champs.example.com:27018')

        connection.initialize()

        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        mock_mongoengine.connect.assert_called_once_with(
            'nbachamps', host='champs.example.com:27018', max_pool_size=max_pool_size,
            replicaSet='real_replica_set')


class TestDatabaseMaxPoolSize(unittest.TestCase):

    def tearDown(self):
        # Reload the configuration so that things are cleaned up properly
        config.load_configuration()
        super(TestDatabaseMaxPoolSize, self).tearDown()

    @patch('pulp.server.db.connection.mongoengine')
    def test_database_max_pool_size_default_is_10(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        host = 'champs.example.com:27018'
        replica_set = ''
        config.config.set('database', 'seeds', host)
        config.config.set('database', 'replica_set', replica_set)

        connection.initialize()

        database = config.config.get('database', 'name')

        mock_mongoengine.connect.assert_called_once_with(database, host=host,
                                                         max_pool_size=10, replicaSet=replica_set)

    @patch('pulp.server.db.connection.mongoengine')
    def test_database_max_pool_size_uses_default(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        host = 'champs.example.com:27018'
        replica_set = ''
        config.config.set('database', 'seeds', host)
        config.config.set('database', 'replica_set', replica_set)

        connection.initialize()

        database = config.config.get('database', 'name')
        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        mock_mongoengine.connect.assert_called_once_with(database, host=host,
                                                         max_pool_size=max_pool_size,
                                                         replicaSet=replica_set)

    @patch('pulp.server.db.connection.mongoengine')
    def test_database_max_pool_size(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        config.config.set('database', 'seeds', 'champs.example.com:27018')
        config.config.set('database', 'replica_set', '')

        connection.initialize(max_pool_size=5)

        database = config.config.get('database', 'name')
        host = config.config.get('database', 'seeds')
        mock_mongoengine.connect.assert_called_once_with(database, host=host,
                                                         max_pool_size=5, replicaSet='')


class TestDatabase(unittest.TestCase):

    def tearDown(self):
        # Reload the configuration so that things are cleaned up properly
        config.load_configuration()
        super(TestDatabase, self).tearDown()

    @patch('pulp.server.db.connection.mongoengine')
    def test_mongoengine_connect_is_called(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        connection.initialize()
        mock_mongoengine.connect.assert_called_once()

    @patch('pulp.server.db.connection.mongoengine')
    def test__DATABASE_is_returned_from_get_db_call(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        connection.initialize()
        expected_database = mock_mongoengine.connection.get_db.return_value
        self.assertTrue(connection._DATABASE is expected_database)
        mock_mongoengine.connection.get_db.assert_called_once_with()

    @patch('pulp.server.db.connection.NamespaceInjector')
    @patch('pulp.server.db.connection.mongoengine')
    def test__DATABASE_receives_namespace_injector(self, mock_mongoengine, mock_namespace_injector):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        connection.initialize()
        mock_son_manipulator = connection._DATABASE.add_son_manipulator
        mock_namespace_injector.assert_called_once_with()
        mock_son_manipulator.assert_called_once_with(mock_namespace_injector.return_value)

    @patch('pulp.server.db.connection.mongoengine')
    def test__DATABASE_collection_names_is_called(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        connection.initialize()
        connection._DATABASE.collection_names.assert_called_once_with()

    @patch('pulp.server.db.connection.mongoengine')
    @patch('pulp.server.db.connection._logger')
    def test_unexpected_Exception_is_logged(self, mock__logger, mock_mongoengine):
        mock_mongoengine.connect.side_effect = IOError()
        self.assertRaises(IOError, connection.initialize)
        self.assertTrue(connection._CONNECTION is None)
        self.assertTrue(connection._DATABASE is None)
        mock__logger.critical.assert_called_once()


class TestDatabaseSSL(unittest.TestCase):

    def tearDown(self):
        # Reload the configuration so that things are cleaned up properly
        config.load_configuration()
        super(TestDatabaseSSL, self).tearDown()

    def test_ssl_off_by_default(self):
        self.assertEqual(config.config.getboolean('database', 'ssl'), False)

    @patch('pulp.server.db.connection.mongoengine')
    def test_ssl_is_skipped_if_off(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        host = 'champs.example.com:27018'
        replica_set = ''
        config.config.set('database', 'ssl', 'false')
        config.config.set('database', 'seeds', host)
        config.config.set('database', 'replica_set', replica_set)

        connection.initialize()

        database = config.config.get('database', 'name')
        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        mock_mongoengine.connect.assert_called_once_with(database, max_pool_size=max_pool_size,
                                                         host=host, replicaSet=replica_set)

    @patch('pulp.server.db.connection.ssl')
    @patch('pulp.server.db.connection.mongoengine')
    def test_ssl_is_configured_with_verify_ssl_on(self, mock_mongoengine, mock_ssl):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        host = 'champs.example.com:27018'
        replica_set = ''
        config.config.set('database', 'verify_ssl', 'true')
        config.config.set('database', 'ssl', 'true')
        config.config.set('database', 'seeds', host)
        config.config.set('database', 'replica_set', replica_set)

        connection.initialize()

        database = config.config.get('database', 'name')
        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        ssl_cert_reqs = mock_ssl.CERT_REQUIRED
        ssl_ca_certs = config.config.get('database', 'ca_path')
        mock_mongoengine.connect.assert_called_once_with(
            database, max_pool_size=max_pool_size, ssl=True, ssl_cert_reqs=ssl_cert_reqs,
            ssl_ca_certs=ssl_ca_certs, host=host, replicaSet=replica_set)

    @patch('pulp.server.db.connection.ssl')
    @patch('pulp.server.db.connection.mongoengine')
    def test_ssl_is_configured_with_verify_ssl_off(self, mock_mongoengine, mock_ssl):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        host = 'champs.example.com:27018'
        replica_set = ''
        config.config.set('database', 'verify_ssl', 'false')
        config.config.set('database', 'ssl', 'true')
        config.config.set('database', 'seeds', host)
        config.config.set('database', 'replica_set', replica_set)

        connection.initialize()

        database = config.config.get('database', 'name')
        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        ssl_cert_reqs = mock_ssl.CERT_NONE
        ssl_ca_certs = config.config.get('database', 'ca_path')
        mock_mongoengine.connect.assert_called_once_with(
            database, max_pool_size=max_pool_size, ssl=True, ssl_cert_reqs=ssl_cert_reqs,
            ssl_ca_certs=ssl_ca_certs, host=host, replicaSet=replica_set)

    @patch('pulp.server.db.connection.ssl')
    @patch('pulp.server.db.connection.mongoengine')
    def test_ssl_is_configured_with_ssl_keyfile(self, mock_mongoengine, mock_ssl):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        host = 'champs.example.com:27018'
        replica_set = ''
        config.config.set('database', 'ssl_keyfile', 'keyfilepath')
        config.config.set('database', 'verify_ssl', 'false')
        config.config.set('database', 'ssl', 'true')
        config.config.set('database', 'seeds', host)
        config.config.set('database', 'replica_set', replica_set)

        connection.initialize()

        database = config.config.get('database', 'name')
        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        ssl_cert_reqs = mock_ssl.CERT_NONE
        ssl_ca_certs = config.config.get('database', 'ca_path')
        mock_mongoengine.connect.assert_called_once_with(
            database, max_pool_size=max_pool_size, ssl=True, ssl_cert_reqs=ssl_cert_reqs,
            ssl_ca_certs=ssl_ca_certs, ssl_keyfile='keyfilepath', host=host,
            replicaSet=replica_set)

    @patch('pulp.server.db.connection.ssl')
    @patch('pulp.server.db.connection.mongoengine')
    def test_ssl_is_configured_with_ssl_certfile(self, mock_mongoengine, mock_ssl):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        host = 'champs.example.com:27018'
        replica_set = ''
        config.config.set('database', 'ssl_certfile', 'certfilepath')
        config.config.set('database', 'verify_ssl', 'false')
        config.config.set('database', 'ssl', 'true')
        config.config.set('database', 'seeds', host)
        config.config.set('database', 'replica_set', replica_set)

        connection.initialize()

        database = config.config.get('database', 'name')
        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        ssl_cert_reqs = mock_ssl.CERT_NONE
        ssl_ca_certs = config.config.get('database', 'ca_path')
        mock_mongoengine.connect.assert_called_once_with(
            database, max_pool_size=max_pool_size, ssl=True, ssl_cert_reqs=ssl_cert_reqs,
            ssl_ca_certs=ssl_ca_certs, ssl_certfile='certfilepath', host=host,
            replicaSet=replica_set)


class TestDatabaseVersion(unittest.TestCase):

    """
    test DB version parsing. Info on expected versions is at
    https://github.com/mongodb/mongo/blob/master/src/mongo/util/version.cpp#L39-45
    """
    @patch('pulp.server.db.connection.mongoengine')
    def _test_initialize(self, version_str, mock_mongoengine):
        mock_mongoclient_connect = mock_mongoengine.connect.return_value
        mock_mongoclient_connect.server_info.return_value = {'version': version_str}
        connection.initialize()

    def test_database_version_bad_version(self):
        try:
            self._test_initialize('1.2.3')
            self.fail("RuntimeError not raised")
        except RuntimeError:
            pass  # expected exception

    def test_database_version_good_version(self):
        # the version check succeeded if no exception was raised
        self._test_initialize('2.6.0')

    def test_database_version_good_equal_version(self):
        # the version check succeeded if no exception was raised
        self._test_initialize('2.4.0')

    def test_database_version_good_rc_version(self):
        # the version check succeeded if no exception was raised
        self._test_initialize('2.8.0-rc1')

    def test_database_version_bad_rc_version(self):
        try:
            self._test_initialize('2.3.0-rc1')
            self.fail("RuntimeError not raised")
        except RuntimeError:
            pass  # expected exception


class TestDatabaseAuthentication(unittest.TestCase):

    def tearDown(self):
        # Reload the configuration so that things are cleaned up properly
        config.load_configuration()
        super(TestDatabaseAuthentication, self).tearDown()

    @patch('pulp.server.db.connection.mongoengine')
    def test_initialize_username_and_password(self, mock_mongoengine):
        mock_mongoengine_instance = mock_mongoengine.connect.return_value
        mock_mongoengine_instance.server_info.return_value = {"version":
                                                              MONGO_MIN_TEST_VERSION}
        config.config.set('database', 'name', 'nbachamps')
        config.config.set('database', 'username', 'larrybird')
        config.config.set('database', 'password', 'celtics1981')
        config.config.set('database', 'seeds', 'champs.example.com:27018')
        config.config.set('database', 'replica_set', '')

        connection.initialize()

        mock_mongoengine.connect.assert_called_once_with(
            'nbachamps', username='larrybird', host='champs.example.com:27018',
            password='celtics1981', max_pool_size=10, replicaSet='')

    @patch('pulp.server.db.connection._logger.debug')
    @patch('pulp.server.db.connection.mongoengine')
    def test_initialize_username_and_shadows_password(self, mock_mongoengine, mock_log):
        mock_mongoengine_instance = mock_mongoengine.connect.return_value
        mock_mongoengine_instance.server_info.return_value = {"version":
                                                              MONGO_MIN_TEST_VERSION}
        config.config.set('database', 'name', 'nbachamps')
        config.config.set('database', 'username', 'larrybird')
        config.config.set('database', 'password', 'celtics1981')
        config.config.set('database', 'seeds', 'champs.example.com:27018')
        config.config.set('database', 'replica_set', '')

        connection.initialize()

        mock_mongoengine.connect.assert_called_once_with(
            'nbachamps', username='larrybird', host='champs.example.com:27018',
            password='celtics1981', max_pool_size=10, replicaSet='')
        expected_calls = [
            call('Attempting username and password authentication.'),
            call("Connection Arguments: {'username': 'larrybird', 'host': "
                 "'champs.example.com:27018', 'password': '*****', 'max_pool_size': 10, "
                 "'replicaSet': ''}"),
            call('Querying the database to validate the connection.')]
        mock_log.assert_has_calls(expected_calls)

    @patch('pulp.server.db.connection.mongoengine')
    def test_initialize_no_username_or_password(self, mock_mongoengine):
        mock_mongoengine_instance = mock_mongoengine.connect.return_value
        mock_mongoengine_instance.server_info.return_value = {"version":
                                                              MONGO_MIN_TEST_VERSION}
        config.config.set('database', 'username', '')
        config.config.set('database', 'password', '')
        connection.initialize()
        self.assertFalse(connection._DATABASE.authenticate.called)

    @patch('pulp.server.db.connection.mongoengine')
    def test_initialize_username_no_password(self, mock_mongoengine):
        mock_mongoengine_instance = mock_mongoengine.connect.return_value
        mock_mongoengine_instance.server_info.return_value = {"version":
                                                              MONGO_MIN_TEST_VERSION}
        config.config.set('database', 'username', 'admin')
        config.config.set('database', 'password', '')
        # ensure no exception is raised (redmine #708)
        connection.initialize()

    @patch('pulp.server.db.connection.mongoengine')
    def test_initialize_password_no_username(self, mock_mongoengine):
        mock_mongoengine_instance = mock_mongoengine.connect.return_value
        mock_mongoengine_instance.server_info.return_value = {"version":
                                                              MONGO_MIN_TEST_VERSION}
        config.config.set('database', 'username', '')
        config.config.set('database', 'password', 'foo')
        self.assertRaises(Exception, connection.initialize)

    @patch('pulp.server.db.connection.OperationFailure', new=MongoEngineConnectionError)
    @patch('pulp.server.db.connection.mongoengine')
    def test_authentication_fails_with_RuntimeError(self, mock_mongoengine):
        mock_mongoengine_instance = mock_mongoengine.connect.return_value
        mock_mongoengine_instance.server_info.return_value = {"version":
                                                              MONGO_MIN_TEST_VERSION}
        exc = MongoEngineConnectionError()
        exc.code = 18
        mock_mongoengine.connection.get_db.side_effect = exc
        self.assertRaises(RuntimeError, connection.initialize)


class TestDatabaseRetryOnInitialConnectionSupport(unittest.TestCase):

    @patch('pulp.server.db.connection.mongoengine')
    def test_retry_waits_when_mongoengine_connection_error_is_raised(self, mock_mongoengine):
        def break_out_on_second(*args, **kwargs):
            mock_mongoengine.connect.side_effect = StopIteration()
            raise MongoEngineConnectionError()

        mock_mongoengine.connect.side_effect = break_out_on_second
        mock_mongoengine.connection.ConnectionError = MongoEngineConnectionError

        self.assertRaises(StopIteration, connection.initialize)

    @patch('pulp.server.db.connection.time.sleep')
    @patch('pulp.server.db.connection.mongoengine')
    def test_retry_sleeps_with_backoff(self, mock_mongoengine, mock_sleep):
        def break_out_on_second(*args, **kwargs):
            mock_sleep.side_effect = StopIteration()

        mock_sleep.side_effect = break_out_on_second
        mock_mongoengine.connect.side_effect = MongoEngineConnectionError()
        mock_mongoengine.connection.ConnectionError = MongoEngineConnectionError

        self.assertRaises(StopIteration, connection.initialize)
        mock_sleep.assert_has_calls([call(1), call(2)])

    @patch('pulp.server.db.connection.time.sleep')
    @patch('pulp.server.db.connection.mongoengine')
    def test_retry_with_max_timeout(self, mock_mongoengine, mock_sleep):
        def break_out_on_second(*args, **kwargs):
            mock_sleep.side_effect = StopIteration()

        mock_sleep.side_effect = break_out_on_second
        mock_mongoengine.connect.side_effect = MongoEngineConnectionError()
        mock_mongoengine.connection.ConnectionError = MongoEngineConnectionError

        self.assertRaises(StopIteration, connection.initialize, max_timeout=1)
        mock_sleep.assert_has_calls([call(1), call(1)])

    @patch('pulp.server.db.connection.mongoengine')
    @patch('pulp.server.db.connection.itertools')
    def test_retry_uses_itertools_chain_and_repeat(self, mock_itertools, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        connection.initialize()
        mock_itertools.repeat.assert_called_once_with(32)
        mock_itertools.chain.assert_called_once_with([1, 2, 4, 8, 16],
                                                     mock_itertools.repeat.return_value)


class TestGetDatabaseFunction(unittest.TestCase):

    @patch('pulp.server.db.connection._DATABASE')
    def test_get_database(self, mock__DATABASE):
        self.assertEqual(mock__DATABASE, connection.get_database())


class TestGetConnectionFunction(unittest.TestCase):

    @patch('pulp.server.db.connection._CONNECTION')
    def test_get_connection(self, mock__CONNECTION):
        self.assertEqual(mock__CONNECTION, connection.get_connection())


@patch('pulp.server.db.connection.UnsafeRetry._decorated_methods', new=('one', 'two'))
@patch('pulp.server.db.connection.config.config')
class TestUnsafeRetry(unittest.TestCase):
    """
    Tests for the unsafe retry feature.
    """

    @patch('pulp.server.db.connection.UnsafeRetry.retry_decorator')
    def test_decorate_instance_retry_off(self, m_retry, m_config):
        """
        Database calls should not be wrapped if the feature has not been turned on.
        """
        m_config.getboolean.return_value = False
        m_instance = MagicMock()
        connection.UnsafeRetry.decorate_instance(m_instance, 'test_collection')
        self.assertFalse(m_retry.called)

    @patch('pulp.server.db.connection.UnsafeRetry.retry_decorator')
    def test_decorate_instance_retry_on(self, m_retry, m_config):
        """
        Database calls should be wrapped if the feature has been turned on.
        """
        m_config.getboolean.return_value = True
        m_instance = MagicMock()
        connection.UnsafeRetry.decorate_instance(m_instance, 'test_collection')
        self.assertTrue(m_instance.one is m_retry.return_value.return_value)
        self.assertTrue(m_instance.two is m_retry.return_value.return_value)

    @patch('pulp.server.db.connection.UnsafeRetry.retry_decorator')
    def test_decorate_instance_retry_on_incomplete_attrs(self, m_retry, m_config):
        """
        Instances without all decorated methods should still be wrapped.
        """
        m_config.getboolean.return_value = True
        m_instance = MagicMock()
        del m_instance.one
        connection.UnsafeRetry.decorate_instance(m_instance, 'test_collection')
        self.assertTrue(m_instance.two is m_retry.return_value.return_value)
        self.assertRaises(AttributeError, getattr, m_instance, 'one')

    @patch('pulp.server.db.connection._logger')
    def test_retry_decorator(self, m_logger, m_config):
        """
        Raise AutoReconnect once (simulate no connection to db), hijack the logger to fix the mock
        so it is not an infinite loop.
        """
        mock_r = MagicMock()
        mock_r.side_effect = AutoReconnect

        def restart_mongo(*args):
            """
            Simulate turning Mongo back on.
            """
            mock_r.side_effect = None
            mock_r.return_value = 'final'

        @connection.UnsafeRetry.retry_decorator(full_name='mock_coll')
        def mock_func():
            """
            Simple function to decorate.
            """
            return mock_r()

        m_config.getboolean.return_value = True
        m_logger.error.side_effect = restart_mongo

        final_answer = mock_func()
        m_logger.error.assert_called_once_with('mock_func operation failed on mock_coll')
        self.assertTrue(final_answer is 'final')
