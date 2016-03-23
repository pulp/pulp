# -*- coding: utf-8 -*-

from unittest import TestCase

from mock import patch, Mock
from nectar import config
from nectar.downloaders import local, threaded

from pulp.common.plugins import importer_constants
from pulp.plugins.importer import Importer


class TestBuildDownloader(TestCase):
    """
    This class contains tests for pulp.plugins.importer.Importer.build_downloader().
    """
    def test_http(self):
        """
        Test with http:// as the scheme.
        """
        url = 'http://martin.com/test'
        nectar_config = config.DownloaderConfig(max_speed=42)

        downloader = Importer.build_downloader(url, nectar_config)

        self.assertTrue(isinstance(downloader, threaded.HTTPThreadedDownloader))
        self.assertEqual(downloader.config.max_speed, 42)

    # This mock allows us to use fake paths to the TLS certs/key. Without it, Nectar tries to read
    # them when the DownloaderConfig is instantiated.
    @patch('nectar.config.DownloaderConfig._process_ssl_settings')
    def test_https(self, _process_ssl_settings):
        """
        Test with https:// as the scheme.
        """
        url = 'https://martin.com/test'
        nectar_config = config.DownloaderConfig(
            ssl_ca_cert='CA Cert', ssl_ca_cert_path='/path/to/ca.crt',
            ssl_client_cert='Client Cert', ssl_client_cert_path='/path/to/client.crt',
            ssl_client_key='Client Cert', ssl_client_key_path='/path/to/client.key')

        downloader = Importer.build_downloader(url, nectar_config)

        self.assertTrue(isinstance(downloader, threaded.HTTPThreadedDownloader))
        self.assertEqual(downloader.config.ssl_ca_cert_path, '/path/to/ca.crt')
        self.assertEqual(downloader.config.ssl_client_cert_path, '/path/to/client.crt')
        self.assertEqual(downloader.config.ssl_client_key_path, '/path/to/client.key')
        _process_ssl_settings.assert_called_once_with()

    def test_invalid_scheme(self):
        """
        Test with an invalid scheme in the URL.
        """
        url = 'ftpx://martin.com/test'
        nectar_config = config.DownloaderConfig(max_speed=42)

        self.assertRaises(ValueError, Importer.build_downloader, url, nectar_config)

    def test_local(self):
        """
        Test with a file:// scheme.
        """
        url = 'file:///martin.com/test'
        nectar_config = config.DownloaderConfig(max_concurrent=23)

        downloader = Importer.build_downloader(url, nectar_config)

        self.assertTrue(isinstance(downloader, local.LocalFileDownloader))
        self.assertEqual(downloader.config.max_concurrent, 23)


class TestCancelSyncRepo(TestCase):
    """
    This class contains tests for pulp.plugins.importer.Importer.cancel_sync_repo().
    """
    @patch('pulp.plugins.importer.sys.exit', autospec=True)
    def test_cancel_sync_repo_calls_sys_exit(self, mock_sys_exit):
        Importer().cancel_sync_repo()
        mock_sys_exit.assert_called_once_with()


class TestGetDownloader(TestCase):
    """
    This class contains tests for pulp.plugins.importer.Importer.get_downloader().
    """

    @patch('pulp.plugins.importer.LocalFileDownloader')
    @patch('pulp.plugins.importer.importer_config_to_nectar_config')
    def test_get_local_downloader(self, to_nectar, local):
        url = 'file:///martin.com/test'
        config = Mock()

        # test
        downloader = Importer.get_downloader(config, url)

        # validation
        to_nectar.assert_called_once_with(config.flatten.return_value, working_dir=None)
        local.assert_called_once_with(to_nectar.return_value)
        self.assertEqual(downloader, local.return_value)

    @patch('pulp.plugins.importer.HTTPThreadedDownloader')
    @patch('pulp.plugins.importer.importer_config_to_nectar_config')
    def test_get_http_downloader(self, to_nectar, http):
        url = 'http://martin.com/test'
        config = Mock()

        # test
        downloader = Importer.get_downloader(config, url)

        # validation
        to_nectar.assert_called_once_with(config.flatten.return_value, working_dir=None)
        http.assert_called_once_with(to_nectar.return_value)
        self.assertEqual(downloader, http.return_value)

    @patch('pulp.plugins.importer.HTTPThreadedDownloader')
    @patch('pulp.plugins.importer.importer_config_to_nectar_config')
    def test_get_https_downloader(self, to_nectar, http):
        url = 'https://martin.com/test'
        config = Mock()

        # test
        downloader = Importer.get_downloader(config, url)

        # validation
        to_nectar.assert_called_once_with(config.flatten.return_value, working_dir=None)
        http.assert_called_once_with(to_nectar.return_value)
        self.assertEqual(downloader, http.return_value)

    @patch('pulp.plugins.importer.importer_config_to_nectar_config', Mock())
    def test_get_downloader_invalid_scheme(self):
        url = 'ftpx://martin.com/test'
        self.assertRaises(ValueError, Importer.get_downloader, Mock(), url)


class TestGetDownloaderForDBImporter(TestCase):
    """
    This class contains tests for pulp.plugins.importer.Importer.get_downloader_for_db_importer().
    """
    def test_http(self):
        """
        Test with http:// as the scheme.
        """
        url = 'http://martin.com/test'
        importer = Mock()
        importer.config = {importer_constants.KEY_MAX_SPEED: 5555}

        downloader = Importer.get_downloader_for_db_importer(importer, url, '/working/dir')

        self.assertTrue(isinstance(downloader, threaded.HTTPThreadedDownloader))
        self.assertEqual(downloader.config.max_speed, 5555)
        self.assertEqual(downloader.config.working_dir, '/working/dir')

    # This mock allows us to use fake paths to the TLS certs/key. Without it, Nectar tries to read
    # them when the DownloaderConfig is instantiated.
    @patch('nectar.config.DownloaderConfig._process_ssl_settings')
    def test_https(self, _process_ssl_settings):
        """
        Test with https:// as the scheme.
        """
        url = 'https://martin.com/test'
        importer = Mock()
        importer.config = {
            importer_constants.KEY_SSL_CA_CERT: 'CA Cert',
            importer_constants.KEY_SSL_CLIENT_CERT: 'Client Cert',
            importer_constants.KEY_SSL_CLIENT_KEY: 'Client Key'}
        importer.tls_ca_cert_path = '/path/to/ca.crt'
        importer.tls_client_cert_path = '/path/to/client.crt'
        importer.tls_client_key_path = '/path/to/client.key'

        downloader = Importer.get_downloader_for_db_importer(importer, url, '/working/dir')

        self.assertTrue(isinstance(downloader, threaded.HTTPThreadedDownloader))
        self.assertEqual(downloader.config.ssl_ca_cert_path, '/path/to/ca.crt')
        self.assertEqual(downloader.config.ssl_client_cert_path, '/path/to/client.crt')
        self.assertEqual(downloader.config.ssl_client_key_path, '/path/to/client.key')
        self.assertEqual(downloader.config.working_dir, '/working/dir')
        _process_ssl_settings.assert_called_once_with()

    def test_invalid_scheme(self):
        """
        Test with an invalid scheme in the URL.
        """
        url = 'ftpx://martin.com/test'
        importer = Mock()
        importer.config = {}

        self.assertRaises(ValueError, Importer.get_downloader_for_db_importer, importer, url,
                          '/working/dir')

    def test_local(self):
        """
        Test with a file:// scheme.
        """
        url = 'file:///martin.com/test'
        importer = Mock()
        importer.config = {importer_constants.KEY_MAX_DOWNLOADS: 123}

        downloader = Importer.get_downloader_for_db_importer(importer, url, '/working/dir')

        self.assertTrue(isinstance(downloader, local.LocalFileDownloader))
        self.assertEqual(downloader.config.max_concurrent, 123)
        self.assertEqual(downloader.config.working_dir, '/working/dir')
