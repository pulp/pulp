# -*- coding: utf-8 -*-
# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import unittest

from nectar.config import DownloaderConfig

from pulp.common.plugins import importer_constants as constants
from pulp.plugins.util import nectar_config


class ConfigTranslationTests(unittest.TestCase):

    def test_importer_config_to_nectar_config_complete(self):
        # Setup
        importer_config = {
            constants.KEY_SSL_CA_CERT : 'ca_cert',
            constants.KEY_SSL_VALIDATION : True,
            constants.KEY_SSL_CLIENT_CERT : 'client_cert',
            constants.KEY_SSL_CLIENT_KEY : 'client_key',

            constants.KEY_PROXY_HOST : 'proxy',
            constants.KEY_PROXY_PORT : 8080,
            constants.KEY_PROXY_USER : 'user',
            constants.KEY_PROXY_PASS : 'pass',

            constants.KEY_MAX_DOWNLOADS : 10,
            constants.KEY_MAX_SPEED : 1024,
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
        self.assertEqual(download_config.max_concurrent, 10)
        self.assertEqual(download_config.max_speed, 1024)

    def test_importer_config_to_download_config_partial(self):
        # Setup
        importer_config = {
            constants.KEY_SSL_CA_CERT : 'ca_cert',
            constants.KEY_PROXY_HOST : 'proxy',
            constants.KEY_MAX_DOWNLOADS : 10,
        }

        # Test
        download_config = nectar_config.importer_config_to_nectar_config(importer_config)

        # Verify
        self.assertEqual(download_config.ssl_ca_cert, 'ca_cert')
        self.assertEqual(download_config.proxy_url, 'proxy')
        self.assertEqual(download_config.max_concurrent, 10)

        self.assertEqual(download_config.proxy_username, None) # spot check
