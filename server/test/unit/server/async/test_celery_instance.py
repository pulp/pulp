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
