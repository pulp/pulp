"""
This module contains tests for the pulp.server.async.celery_instance module.
"""
from datetime import timedelta
from functools import partial
import ssl
import unittest

import mock

from pulp.server.async import celery_instance
from pulp.server.config import config, _default_values
from pulp.server.db.reaper import queue_reap_expired_documents
from pulp.server.maintenance.monthly import queue_monthly_maintenance


class TestCelerybeatSchedule(unittest.TestCase):
    """
    Assert that the CELERYBEAT_SCHEDULE structure has the expected tasks in it.
    """
    def test_num_tasks(self):
        """
        Assert that the expected number of beat tasks are in the CELERYBEAT_SCHEDULE. If you find
        youself adjusting this test because you added a new task to CELERYBEAT_SCHEDULE, please do
        add another unit test to this test class asserting that your new task is present with the
        correct information. Thanks!
        """
        # Please read the docblock to this test if you find yourself needing to adjust this
        # assertion.
        self.assertEqual(len(celery_instance.celery.conf['CELERYBEAT_SCHEDULE']), 2)

    def test_reap_expired_documents(self):
        """
        Make sure the reap_expired_documents Task is present and properly configured.
        """
        reap = celery_instance.celery.conf['CELERYBEAT_SCHEDULE']['reap_expired_documents']
        expected_reap = {
            'task': queue_reap_expired_documents.name,
            'schedule': timedelta(days=(config.getfloat('data_reaping', 'reaper_interval'))),
            'args': tuple(),
        }
        self.assertEqual(reap, expected_reap)

    def test_monthly_maintenance(self):
        """
        Make sure the monthly maintenance Task is present and properly configured.
        """
        expected_monthly_maintenance = {
            'task': queue_monthly_maintenance.name,
            'schedule': timedelta(days=30),
            'args': tuple(),
        }
        self.assertEqual(celery_instance.celery.conf['CELERYBEAT_SCHEDULE']['monthly_maintenance'],
                         expected_monthly_maintenance)

    def test_celery_conf_updated(self):
        """
        Make sure the Celery config was updated with our CELERYBEAT_SCHEDULE.
        """
        self.assertEqual(celery_instance.celery.conf['CELERYBEAT_SCHEDULE'],
                         celery_instance.CELERYBEAT_SCHEDULE)


def fake_get(new_config, section, key):
    """
    Fake version of the get() method from pulp's config object. This is useful
    so we can have concrete values to test for.
    """
    if section in new_config.keys() and new_config[section].get(key, False):
        return new_config[section].get(key)
    else:
        return _default_values[section][key]


def _get_database_test_config():
    """
    Returns a configuration that contains a definition for the 'database' section of the config.

    This is a method so that every copy returned is independent since the caller usually modifies
    it some.

    :return: A dict containing configuration values for the 'database' section.
    :rtype dict
    """
    config = {
        'database': {
            'name': 'database_name',
            'seeds': 'host1:27017,host2:27017',
            'username': 'someguy',
            'password': 'letmein',
            }
    }
    return config


class TestCeleryInstanceSSLConfig(unittest.TestCase):
    """
    Assert that the BROKER_USE_SSL structure has the expected configuration in it.
    """

    @mock.patch('pulp.server.async.celery_instance.config.getboolean')
    def test_configure_SSL_when_SSL_disabled(self, mock_getboolean):
        """
        Make sure that the Celery config has BROKER_USE_SSL set to False if SSL is disabled.
        """
        mock_getboolean.return_value = False
        celery_instance.configure_SSL()
        self.assertFalse(celery_instance.celery.conf['BROKER_USE_SSL'])

    @mock.patch('pulp.server.async.celery_instance.celery')
    @mock.patch('pulp.server.async.celery_instance.config.getboolean')
    def test_configure_SSL_when_SSL_enabled(self, mock_getboolean, mock_celery):
        """
        Make sure that the Celery config has BROKER_USE_SSL properly formed if SSL enabled.
        """
        mock_getboolean.return_value = True
        mock_cacert = mock.Mock()
        mock_keyfile = mock.Mock()
        mock_certfile = mock.Mock()

        CONFIG_OVERRIDE = {
            'tasks': {
                'cacert': mock_cacert,
                'keyfile': mock_keyfile,
                'certfile': mock_certfile,
                'cert_reqs': ssl.CERT_REQUIRED,
                }
        }

        EXPECTED_BROKER_USE_SSL = {
            'ca_certs': mock_cacert,
            'keyfile': mock_keyfile,
            'certfile': mock_certfile,
            'cert_reqs': ssl.CERT_REQUIRED,
        }

        custom_fake_get = partial(fake_get, CONFIG_OVERRIDE)

        with mock.patch('pulp.server.async.celery_instance.config.get', new=custom_fake_get):
            celery_instance.configure_SSL()
            mock_celery.conf.update.assert_called_once_with(BROKER_USE_SSL=EXPECTED_BROKER_USE_SSL)


class TestMongoBackendConfig(unittest.TestCase):

    def test_celery_cong_updated(self):
        """
        Assert the celery_config is updated with the necessary settings.
        """
        self.assertEqual(celery_instance.celery.conf['CELERY_RESULT_BACKEND'], 'mongodb')
        self.assertTrue(
            isinstance(celery_instance.celery.conf['CELERY_MONGODB_BACKEND_SETTINGS'], dict))

        conf = celery_instance.celery.conf['CELERY_MONGODB_BACKEND_SETTINGS']

        self.assertTrue(conf.get('host') is not None)
        self.assertTrue(conf.get('database') is not None)

    @mock.patch('pulp.server.async.celery_instance.config.has_option', new=lambda x, y: True)
    def test_create_config(self):
        """
        Assert that the mongo config is created correctly with correct settings.
        """
        custom_fake_get = partial(fake_get, _get_database_test_config())
        with mock.patch('pulp.server.async.celery_instance.config.get', new=custom_fake_get):
            result = celery_instance.create_mongo_config()

            self.assertEqual(result['host'], 'host1')
            self.assertEqual(result['port'], '27017')
            self.assertEqual(result['database'], 'database_name')
            self.assertEqual(result['user'], 'someguy')
            self.assertEqual(result['password'], 'letmein')

    @mock.patch('pulp.server.async.celery_instance.config.has_option', new=lambda x, y: True)
    def test_create_config_one_seed(self):
        """
        Assert that port and host are set on the mongo config with only one host:port specified.
        """
        config = _get_database_test_config()
        config['database']['seeds'] = config['database']['seeds'].split(',')[0]
        custom_fake_get = partial(fake_get, config)
        with mock.patch('pulp.server.async.celery_instance.config.get', new=custom_fake_get):
            result = celery_instance.create_mongo_config()

            self.assertEqual(result['host'], 'host1')
            self.assertEqual(result['port'], '27017')

    @mock.patch('pulp.server.async.celery_instance.config.has_option', new=lambda x, y: True)
    def test_create_config_no_port(self):
        """
        Assert a seed that does not have a port does not set the port on the mongo config.
        """
        config = _get_database_test_config()
        config['database']['seeds'] = 'host1'
        custom_fake_get = partial(fake_get, config)
        with mock.patch('pulp.server.async.celery_instance.config.get', new=custom_fake_get):
            result = celery_instance.create_mongo_config()

            self.assertEqual(result['host'], 'host1')
            self.assertTrue('port' not in result)

    @mock.patch('pulp.server.async.celery_instance.config.has_option',
                new=lambda x, y: False if y == 'password' else True)
    def test_no_password(self):
        """
        Assert both user and password are missing from the mongo config if password is missing.
        """
        custom_fake_get = partial(fake_get, _get_database_test_config())
        with mock.patch('pulp.server.async.celery_instance.config.get', new=custom_fake_get):
            result = celery_instance.create_mongo_config()

            self.assertTrue('user' not in result)
            self.assertTrue('password' not in result)

    @mock.patch('pulp.server.async.celery_instance.config.has_option',
                new=lambda x, y: False if y == 'username' else True)
    def test_no_user(self):
        """
        Assert both user and password are missing mongo config if username is missing.
        """
        custom_fake_get = partial(fake_get, _get_database_test_config())
        with mock.patch('pulp.server.async.celery_instance.config.get', new=custom_fake_get):
            result = celery_instance.create_mongo_config()

            self.assertTrue('user' not in result)
            self.assertTrue('password' not in result)

    @mock.patch('pulp.server.async.celery_instance.config.getboolean', return_value=True)
    def test_ssl_ca_path(self, getboolean):
        """
        Assert correct behavior when a ca_path is provided.
        """
        config = {'database': {'ca_path': '/some/ca.pem'}}
        custom_fake_get = partial(fake_get, config)

        with mock.patch('pulp.server.async.celery_instance.config.get', new=custom_fake_get):
            result = celery_instance.create_mongo_config()

            self.assertEqual(result['ssl_ca_certs'], config['database']['ca_path'])

    @mock.patch('pulp.server.async.celery_instance.config.getboolean', return_value=True)
    def test_ssl_client_cert_and_key(self, getboolean):
        """
        Assert correct behavior when a client cert and key are provided.
        """
        config = {'database': {'ssl_keyfile': '/some/file.key', 'ssl_certfile': '/some/file.crt'}}
        custom_fake_get = partial(fake_get, config)

        with mock.patch('pulp.server.async.celery_instance.config.get', new=custom_fake_get):
            result = celery_instance.create_mongo_config()

            self.assertEqual(result['ssl_keyfile'], config['database']['ssl_keyfile'])
            self.assertEqual(result['ssl_certfile'], config['database']['ssl_certfile'])

    @mock.patch('pulp.server.async.celery_instance.config.getboolean',
                new=lambda x, y: False if y == 'ssl' else True)
    def test_ssl_false(self):
        """
        Assert that no SSL related flags are set if ssl is false.
        """
        result = celery_instance.create_mongo_config()

        for s in ('ssl', 'ssl_keyfile', 'ssl_certfile', 'ssl_cert_reqs', 'ssl_ca_certs'):
            self.assertTrue(s not in result)

    @mock.patch('pulp.server.async.celery_instance.config.getboolean', return_value=True)
    def test_verify_ssl_true(self, getboolean):
        """
        Assert correct behavior when verify_ssl is True.
        """
        result = celery_instance.create_mongo_config()

        self.assertEqual(result['ssl'], True)
        self.assertEqual(result['ssl_cert_reqs'], ssl.CERT_REQUIRED)

    @mock.patch('pulp.server.async.celery_instance.config.getboolean',
                new=lambda x, y: False if y == 'verify_ssl' else True)
    def test_verify_ssl_false(self):
        """
        Assert correct behavior when verify_ssl is False.
        """
        result = celery_instance.create_mongo_config()

        self.assertEqual(result['ssl'], True)
        self.assertEqual(result['ssl_cert_reqs'], ssl.CERT_NONE)
