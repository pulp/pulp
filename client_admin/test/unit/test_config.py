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
from pulp.client.admin.config import read_config, SCHEMA


VALID = """
[server]
host =
port = 443
api_prefix = /pulp/api
verify_ssl = True
ca_path = '/etc/pki/tls/certs/'
upload_chunk_size = 1048576

[client]
role = admin

[filesystem]
extensions_dir = /usr/lib/pulp/admin/extensions
id_cert_dir = ~/.pulp
id_cert_filename = user-cert.pem
upload_working_dir = ~/.pulp/uploads

[logging]
filename = ~/.pulp/admin.log
call_log_filename = ~/.pulp/server_calls.log

[output]
poll_frequency_in_seconds = 1
enable_color = true
wrap_to_terminal = false
wrap_width = 80
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
            '/etc/pulp/admin/admin.conf',
            os.path.expanduser('~/.pulp/admin.conf')
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
