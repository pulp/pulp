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
    @mock.patch('pulp.devel.unit.server.base.override_config_attrs')
    @mock.patch('pulp.devel.unit.server.base.stop_logging')
    @mock.patch('pulp.devel.unit.server.base.start_logging')
    def test_load_test_config(self, start_logging, stop_logging, override):
        """
        Assert correct operation of the function.
        """
        base._load_test_config()

        # Logging should have been started and stopped
        start_logging.assert_called_once_with()
        stop_logging.assert_called_once_with()

        # Ensure that the correct settings have been put into place
        self.assertEqual(config.config.get('database', 'name'), 'pulp_unittest')
        self.assertEqual(config.config.get('server', 'storage_dir'), '/tmp/pulp')

        # Ensure that the config tampering prevention was triggered
        override.assert_called_once_with()


class ConfigAttrOverride(unittest.TestCase):
    def tearDown(self):
        # config altering overrides must be replaced after running these tests
        base.override_config_attrs()

    def test_override_restore(self):
        # override and restore works as expected
        base.override_config_attrs()
        self.assertTrue(config.load_configuration is base._enforce_config)
        self.assertTrue(config.__setattr__ is base._enforce_config)
        self.assertTrue(config.config.set is base._enforce_config)
        self.assertTrue(hasattr(config, '_overridden_attrs'))

        base.restore_config_attrs()
        self.assertTrue(
            config.load_configuration is config._overridden_attrs['load_configuration'])
        self.assertTrue(config.__setattr__ is config._overridden_attrs['__setattr__'])
        self.assertTrue(config.config.set is config._overridden_attrs['config.set'])

    def test_override_reentrant(self):
        # the override/restore interaction is reentrant: override can be called again before
        # restore is called and no further changes will be made, preventing base._enfore_config
        # from being saved as the overridden attrs
        base.override_config_attrs()
        base.override_config_attrs()

        for attr in config._overridden_attrs.values():
            self.assertTrue(attr is not base._enforce_config)

    def test_load_test_config_after_override(self):
        """
        _load_test_config works even when config modifications are disallowed beforehand
        """
        # _load_test_config is able to modify the config even after override is called...
        base.override_config_attrs()
        # If something was wrong, this would raise Exception
        base._load_test_config()
        # but attempts to alter the config afterwatd are still blocked
        self.assertRaises(Exception, config.config.set, 'section', 'key', 'value')


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
