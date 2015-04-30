"""
This module contains tests for pulp.devel.unit.server.base.
"""
import os
import unittest

import mock

from pulp.devel.unit.server import base


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


class LoadTestConfigTestCase(unittest.TestCase):
    """
    This class contains tests for the _load_test_config() function.
    """
    @mock.patch('pulp.devel.unit.server.base.config.add_config_file')
    @mock.patch('pulp.devel.unit.server.base.stop_logging')
    @mock.patch('pulp.devel.unit.server.base.start_logging')
    def test_load_test_config(self, start_logging, stop_logging, add_config_file):
        """
        Assert correct operation of the function.
        """
        base._load_test_config()

        add_config_file.assert_called_once_with(
            os.path.join(base.DATA_DIR, 'test-override-pulp.conf'))
        start_logging.assert_called_once_with()
        stop_logging.assert_called_once_with()


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
