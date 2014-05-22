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
from pulp.server.db.reaper import reap_expired_documents
from pulp.server.maintenance.monthly import monthly_maintenance


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
            'task': reap_expired_documents.name,
            'schedule': timedelta(days=(config.getfloat('data_reaping', 'reaper_interval'))),
            'args': tuple(),
        }
        self.assertEqual(reap, expected_reap)

    def test_monthly_maintenance(self):
        """
        Make sure the monthly maintenance Task is present and properly configured.
        """
        expected_monthly_maintenance = {
            'task': monthly_maintenance.name,
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
    if new_config.get(key):
        return new_config.get(key)
    else:
        return _default_values[section][key]


CONFIG = {
    'name': 'database_name',
    'seeds': 'host1:27017,host2:27017',
    'user': 'someguy',
    'password': 'letmein',
}


class TestCeleryInstanceSSLConfig(unittest.TestCase):
    """
    Assert that the BROKER_USE_SSL structure has the expected configuration in it.
    """

    def test_SSL_not_enabled(self):
        """
        Make sure that the Celery config does not have BROKER_USE_SSL set if SSL is not enabled.
        """
        self.assertFalse(celery_instance.celery.conf['BROKER_USE_SSL'])

    def test_SSL_enabled(self):
        """
        Make sure that the Celery config has BROKER_USE_SSL properly formed if SSL enabled.
        """
        mock_cacert = mock.Mock()
        mock_keyfile = mock.Mock()
        mock_certfile = mock.Mock()
        CONFIG_OVERRIDE = {
            'cacert': mock_cacert,
            'keyfile': mock_keyfile,
            'certfile': mock_certfile,
            'cert_reqs': ssl.CERT_REQUIRED,
            'broker_url': 'qpid://guest@localhost/',
            'celery_require_ssl': 'true',
        }
        EXPECTED_BROKER_USE_SSL = {
            'ca_certs': mock_cacert,
            'keyfile': mock_keyfile,
            'certfile': mock_certfile,
            'cert_reqs': ssl.CERT_REQUIRED,
        }
        custom_fake_get = partial(fake_get, CONFIG_OVERRIDE)
        with mock.patch('pulp.server.async.celery_instance.config.get', new=custom_fake_get):
            reload(celery_instance)
            ACTUAL_BROKER_USE_SSL = celery_instance.celery.conf['BROKER_USE_SSL']
            self.assertEqual(set(EXPECTED_BROKER_USE_SSL.keys()), set(ACTUAL_BROKER_USE_SSL.keys()))
            for key in EXPECTED_BROKER_USE_SSL.keys():
                self.assertEqual(EXPECTED_BROKER_USE_SSL[key], ACTUAL_BROKER_USE_SSL[key])

    def tearDown(self):
        """
        Reload the celery_instance module after each test is run.

        Tests in this class set options that are important at import time for the celery_instance
        module.  This reloads the module back to its correct defaults after each test.
        """
        reload(celery_instance)


class TestMongoBackendConfig(unittest.TestCase):

    def test_celery_conf_updated(self):
        self.assertEqual(celery_instance.celery.conf['CELERY_RESULT_BACKEND'], 'mongodb')
        self.assertTrue(
            isinstance(celery_instance.celery.conf['CELERY_MONGODB_BACKEND_SETTINGS'], dict))

        conf = celery_instance.celery.conf['CELERY_MONGODB_BACKEND_SETTINGS']

        self.assertTrue(conf.get('host') is not None)
        self.assertTrue(conf.get('database') is not None)

    @mock.patch('pulp.server.async.celery_instance.config.has_option', new=lambda x, y: True)
    def test_create_config(self):
        custom_fake_get = partial(fake_get, CONFIG)
        with mock.patch('pulp.server.async.celery_instance.config.get', new=custom_fake_get):
            result = celery_instance.create_mongo_config()

            self.assertEqual(result['host'], 'host1')
            self.assertEqual(result['port'], '27017')
            self.assertEqual(result['database'], 'database_name')
            self.assertEqual(result['user'], 'someguy')
            self.assertEqual(result['password'], 'letmein')

    @mock.patch('pulp.server.async.celery_instance.config.has_option', new=lambda x, y: True)
    def test_create_config_one_seed(self):
        config = CONFIG.copy()
        config['seeds'] = config['seeds'].split(',')[0]
        custom_fake_get = partial(fake_get, config)
        with mock.patch('pulp.server.async.celery_instance.config.get', new=custom_fake_get):
            result = celery_instance.create_mongo_config()

            self.assertEqual(result['host'], 'host1')
            self.assertEqual(result['port'], '27017')

    @mock.patch('pulp.server.async.celery_instance.config.has_option', new=lambda x, y: True)
    def test_create_config_no_port(self):
        config = CONFIG.copy()
        config['seeds'] = 'host1'
        custom_fake_get = partial(fake_get, config)
        with mock.patch('pulp.server.async.celery_instance.config.get', new=custom_fake_get):
            result = celery_instance.create_mongo_config()

            self.assertEqual(result['host'], 'host1')
            self.assertTrue('port' not in result)

    @mock.patch('pulp.server.config.config.has_option',
                new=lambda x, y: False if y == 'password' else True)
    def test_no_password(self):
        custom_fake_get = partial(fake_get, CONFIG)
        with mock.patch('pulp.server.async.celery_instance.config.get', new=custom_fake_get):
            result = celery_instance.create_mongo_config()

            self.assertTrue('user' not in result)
            self.assertTrue('password' not in result)

    @mock.patch('pulp.server.config.config.has_option',
                new=lambda x, y: False if y == 'user' else True)
    def test_no_user(self):
        custom_fake_get = partial(fake_get, CONFIG)
        with mock.patch('pulp.server.async.celery_instance.config.get', new=custom_fake_get):
            result = celery_instance.create_mongo_config()

            self.assertTrue('user' not in result)
            self.assertTrue('password' not in result)
