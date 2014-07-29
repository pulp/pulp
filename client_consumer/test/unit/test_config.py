# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import os

from unittest import TestCase
from cStringIO import StringIO
from iniparse import INIConfig

from mock import patch, Mock

from pulp.common.config import Config
from pulp.client.consumer.config import read_config, SCHEMA, DEFAULT


VALID = """
[server]
host = localhost
port = 443
api_prefix = /pulp/api
verify_ssl = true
ca_path: /etc/pki/tls/certs/

[authentication]
rsa_key = '/tmp/key'
rsa_pub = '/tmp/pub'

[client]
role = consumer

[filesystem]
extensions_dir = /usr/lib/pulp/consumer/extensions
repo_file = /etc/yum.repos.d/pulp.repo
mirror_list_dir = /etc/yum.repos.d
gpg_keys_dir = /etc/pki/pulp-gpg-keys
cert_dir = /etc/pki/pulp/client/repo
id_cert_dir = /etc/pki/pulp/consumer/
id_cert_filename = consumer-cert.pem

[reboot]
permit = False
delay = 3

[logging]
filename = ~/.pulp/consumer.log
call_log_filename = ~/.pulp/consumer_server_calls.log

[output]
poll_frequency_in_seconds = 1
enable_color = true
wrap_to_terminal = false
wrap_width = 80

[messaging]
scheme = tcp
host =
port = 5672
cacert =
clientcert =

[profile]
minutes = 240
"""


class TestConfig(TestCase):

    @patch('pulp.common.config.INIConfig')
    def test_valid(self, mock_config):
        mock_config.return_value = INIConfig(fp=StringIO(VALID))

        # test
        cfg = read_config()

        # validation
        self.assertTrue(isinstance(cfg, Config))
        self.assertEqual(len(cfg), len(SCHEMA))
        self.assertEqual(sorted(cfg.keys()), sorted([s[0] for s in SCHEMA]))
        self.assertEqual(len(cfg), len(DEFAULT))
        self.assertEqual(sorted(cfg.keys()), sorted(DEFAULT.keys()))
        # validate the DEFAULT matches the SCHEMA
        for s in SCHEMA:
            for p in [p[0] for p in s[2]]:
                self.assertTrue(p in DEFAULT[s[0]])

    @patch('pulp.common.config.INIConfig')
    def test_defaulted(self, mock_config):
        mock_config.return_value = INIConfig(fp=StringIO(''))

        # test
        cfg = read_config()

        # validation
        self.assertTrue(isinstance(cfg, Config))
        self.assertEqual(len(cfg), len(SCHEMA))
        self.assertEqual(sorted(cfg.keys()), sorted([s[0] for s in SCHEMA]))

    @patch('pulp.common.config.Config.validate')
    @patch('pulp.common.config.INIConfig')
    def test_validation_option(self, mock_config, mock_validate):
        mock_config.return_value = INIConfig()

        # test
        read_config(validate=False)

        # validation
        self.assertFalse(mock_validate.called)

    @patch('os.path.exists', return_value=True)
    @patch('__builtin__.open')
    @patch('pulp.common.config.Config.validate')
    @patch('pulp.common.config.INIConfig')
    def test_default_paths(self, mock_config, mock_validate, mock_open, *unused):
        mock_config.return_value = INIConfig()

        mock_fp = Mock()
        mock_fp.__enter__ = Mock(return_value=mock_fp)
        mock_fp.__exit__ = Mock()
        mock_open.return_value = mock_fp

        # test
        read_config(validate=False)

        # validation
        paths = [
            '/etc/pulp/consumer/consumer.conf',
            os.path.expanduser('~/.pulp/consumer.conf')
        ]
        mock_open.assert_any(paths[0])
        mock_open.assert_any(paths[1])
        self.assertFalse(mock_validate.called)

    @patch('__builtin__.open')
    @patch('pulp.common.config.Config.validate')
    @patch('pulp.common.config.INIConfig')
    def test_explicit_paths(self, mock_config, mock_validate, mock_open):
        mock_config.return_value = INIConfig()

        mock_fp = Mock()
        mock_fp.__enter__ = Mock(return_value=mock_fp)
        mock_fp.__exit__ = Mock()
        mock_open.return_value = mock_fp

        paths = ['/tmp/a.conf', '/tmp/b.conf']

        # test
        read_config(paths, validate=False)

        # validation

        mock_open.assert_any(paths[0])
        mock_open.assert_any(paths[1])
        self.assertFalse(mock_validate.called)
