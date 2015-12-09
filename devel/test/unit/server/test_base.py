"""
This module contains tests for pulp.devel.unit.server.base.
"""
import unittest

import mock

from pulp.devel.unit.server import base
from pulp.server import config


class DropDatabaseTestCase(unittest.TestCase):
    """
    This class contains tests for the drop_database() function.
    """
    @mock.patch('pulp.devel.unit.server.base.connection._CONNECTION')
    @mock.patch('pulp.devel.unit.server.base.connection._DATABASE')
    def test_drop_database(self, _DATABASE, _CONNECTION):
        """
        Assert that the function drops the database.
        """
        base.drop_database()

        _CONNECTION.drop_database.assert_called_once_with(_DATABASE.name)


class EnforceConfigTestCase(unittest.TestCase):
    """
    This class contains tests for the _enforce_config() function.
    """
    def test_raises_exception(self):
        """
        Ensure that _enforce_config raises an Exception.
        """
        self.assertRaises(Exception, base._enforce_config)


class LoadTestConfigTestCase(unittest.TestCase):
    """
    This class contains tests for the _load_test_config() function.
    """
    @mock.patch('pulp.devel.unit.server.base.config.config.set')
    @mock.patch('pulp.devel.unit.server.base.stop_logging')
    @mock.patch('pulp.devel.unit.server.base.start_logging')
    def test_load_test_config(self, start_logging, stop_logging, config_set):
        """
        Assert correct operation of the function.
        """
        base._load_test_config()

        # Logging should have been started and stopped
        start_logging.assert_called_once_with()
        stop_logging.assert_called_once_with()

        # Ensure that the correct settings have been put into place
        self.assertEqual(
            [c[1] for c in config_set.mock_calls],
            [('database', 'name', 'pulp_unittest'), ('server', 'storage_dir', '/tmp/pulp')])

        # Ensure that the config doesn't allow tampering
        self.assertTrue(config.config.set is base._enforce_config)
        self.assertTrue(config.load_configuration is base._enforce_config)
        self.assertTrue(config.__setattr__ is base._enforce_config)


class StartDatabaseConnectionTestCase(unittest.TestCase):
    """
    This class contains tests for the start_database_connection() function.
    """
    @mock.patch('pulp.devel.unit.server.base.connection._CONNECTION', mock.MagicMock())
    @mock.patch('pulp.devel.unit.server.base._load_test_config')
    @mock.patch('pulp.devel.unit.server.base.connection.initialize')
    def test_initialized(self, initialize, _load_test_config):
        """
        Assert that the function is a noop when the connection is already initialized.
        """
        base.start_database_connection()

        self.assertEqual(_load_test_config.call_count, 0)
        self.assertEqual(initialize.call_count, 0)

    @mock.patch('pulp.devel.unit.server.base.connection._CONNECTION', None)
    @mock.patch('pulp.devel.unit.server.base._load_test_config')
    @mock.patch('pulp.devel.unit.server.base.connection.initialize')
    def test_not_initialized(self, initialize, _load_test_config):
        """
        Assert that the function starts the connection when the connection is not already
        initialized.
        """
        base.start_database_connection()

        _load_test_config.assert_called_once_with()
        initialize.assert_called_once_with()
