# -*- coding: utf-8 -*-

from unittest import TestCase

from mock import patch, Mock

from pulp.plugins.importer import Importer


class TestImporter(TestCase):

    @patch('pulp.plugins.importer.LocalFileDownloader')
    @patch('pulp.plugins.importer.importer_config_to_nectar_config')
    def test_get_local_downloader(self, to_nectar, local):
        url = 'file:///martin.com/test'
        config = Mock()

        # test
        downloader = Importer.get_downloader(config, url)

        # validation
        to_nectar.assert_called_once_with(config.flatten.return_value, working_dir='/tmp')
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
        to_nectar.assert_called_once_with(config.flatten.return_value, working_dir='/tmp')
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
        to_nectar.assert_called_once_with(config.flatten.return_value, working_dir='/tmp')
        http.assert_called_once_with(to_nectar.return_value)
        self.assertEqual(downloader, http.return_value)

    @patch('pulp.plugins.importer.importer_config_to_nectar_config', Mock())
    def test_get_downloader_invalid_scheme(self):
        url = 'ftpx://martin.com/test'
        self.assertRaises(ValueError, Importer.get_downloader, Mock(), url)

    @patch('pulp.plugins.importer.sys.exit', autospec=True)
    def test_cancel_sync_repo_calls_sys_exit(self, mock_sys_exit):
        Importer().cancel_sync_repo()
        mock_sys_exit.assert_called_once_with()
