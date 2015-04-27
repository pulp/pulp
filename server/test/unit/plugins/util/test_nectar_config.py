import unittest

from nectar.config import DownloaderConfig

from pulp.common.plugins import importer_constants as constants
from pulp.plugins.util import nectar_config


class ConfigTranslationTests(unittest.TestCase):

    def test_importer_config_to_nectar_config_complete(self):
        # Setup
        importer_config = {
            constants.KEY_SSL_CA_CERT: 'ca_cert',
            constants.KEY_SSL_VALIDATION: True,
            constants.KEY_SSL_CLIENT_CERT: 'client_cert',
            constants.KEY_SSL_CLIENT_KEY: 'client_key',

            constants.KEY_PROXY_HOST: 'proxy',
            constants.KEY_PROXY_PORT: 8080,
            constants.KEY_PROXY_USER: 'user',
            constants.KEY_PROXY_PASS: 'pass',

            constants.KEY_BASIC_AUTH_USER: 'basicuser',
            constants.KEY_BASIC_AUTH_PASS: 'basicpass',

            constants.KEY_MAX_DOWNLOADS: 10,
            constants.KEY_MAX_SPEED: 1024,
        }

        # Test
        download_config = nectar_config.importer_config_to_nectar_config(importer_config)

        # Verify
        self.assertTrue(isinstance(download_config, DownloaderConfig))
        self.assertEqual(download_config.ssl_ca_cert, 'ca_cert')
        self.assertEqual(download_config.ssl_validation, True)
        self.assertEqual(download_config.ssl_client_cert, 'client_cert')
        self.assertEqual(download_config.ssl_client_key, 'client_key')
        self.assertEqual(download_config.proxy_url, 'proxy')
        self.assertEqual(download_config.proxy_port, 8080)
        self.assertEqual(download_config.proxy_username, 'user')
        self.assertEqual(download_config.proxy_password, 'pass')
        self.assertEqual(download_config.basic_auth_username, 'basicuser')
        self.assertEqual(download_config.basic_auth_password, 'basicpass')
        self.assertEqual(download_config.max_concurrent, 10)
        self.assertEqual(download_config.max_speed, 1024)

    def test_importer_config_to_download_config_partial(self):
        # Setup
        importer_config = {
            constants.KEY_SSL_CA_CERT: 'ca_cert',
            constants.KEY_PROXY_HOST: 'proxy',
            constants.KEY_MAX_DOWNLOADS: 10,
        }

        # Test
        download_config = nectar_config.importer_config_to_nectar_config(importer_config)

        # Verify
        self.assertEqual(download_config.ssl_ca_cert, 'ca_cert')
        self.assertEqual(download_config.proxy_url, 'proxy')
        self.assertEqual(download_config.max_concurrent, 10)

        self.assertEqual(download_config.proxy_username, None)  # spot check
