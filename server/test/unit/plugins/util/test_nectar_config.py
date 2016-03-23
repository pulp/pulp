import shutil
import tempfile
import unittest

from mock import MagicMock, patch
from nectar.config import DownloaderConfig

from pulp.common.plugins import importer_constants as constants
from pulp.plugins.util import nectar_config


class ConfigTranslationTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    # This mock allows us to use fake paths to the TLS certs/key. Without it, Nectar tries to read
    # them when the DownloaderConfig is instantiated.
    @patch('nectar.config.DownloaderConfig._process_ssl_settings')
    def test_importer_to_nectar_config(self, _process_ssl_settings):
        """
        Run importer_to_nectar_config to make sure the TLS settings are used correctly.
        """
        importer = MagicMock()
        importer.config = {
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
        importer.tls_ca_cert_path = '/path/to/ca.crt'
        importer.tls_client_cert_path = '/path/to/client.crt'
        importer.tls_client_key_path = '/path/to/client.key'

        download_config = nectar_config.importer_to_nectar_config(importer, '/working/dir')

        self.assertTrue(isinstance(download_config, DownloaderConfig))
        self.assertEqual(download_config.ssl_ca_cert, None)
        self.assertEqual(download_config.ssl_ca_cert_path, '/path/to/ca.crt')
        self.assertEqual(download_config.ssl_validation, True)
        self.assertEqual(download_config.ssl_client_cert, None)
        self.assertEqual(download_config.ssl_client_cert_path, '/path/to/client.crt')
        self.assertEqual(download_config.ssl_client_key, None)
        self.assertEqual(download_config.ssl_client_key_path, '/path/to/client.key')
        self.assertEqual(download_config.proxy_url, 'proxy')
        self.assertEqual(download_config.proxy_port, 8080)
        self.assertEqual(download_config.proxy_username, 'user')
        self.assertEqual(download_config.proxy_password, 'pass')
        self.assertEqual(download_config.basic_auth_username, 'basicuser')
        self.assertEqual(download_config.basic_auth_password, 'basicpass')
        self.assertEqual(download_config.max_concurrent, 10)
        self.assertEqual(download_config.max_speed, 1024)
        self.assertEqual(download_config.working_dir, '/working/dir')
        _process_ssl_settings.assert_called_once_with()

    @patch('pulp.server.managers.repo._common.get_working_directory', spec_set=True)
    def test_importer_config_to_nectar_config_complete(self, mock_get_working):
        # Setup
        mock_get_working.return_value = self.temp_dir
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

    @patch('pulp.server.managers.repo._common.get_working_directory', spec_set=True)
    def test_importer_config_to_download_config_partial(self, mock_get_working):
        # Setup
        mock_get_working.return_value = self.temp_dir
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
