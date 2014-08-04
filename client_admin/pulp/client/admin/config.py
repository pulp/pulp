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
import socket

from pulp.common.config import Config, REQUIRED, ANY, NUMBER, BOOL, OPTIONAL

DEFAULT = {
    'server': {
        'host': socket.gethostname(),
        'port': '443',
        'api_prefix': '/pulp/api',
        'verify_ssl': 'true',
        'ca_path': '/etc/pki/tls/certs/',
        'upload_chunk_size': '1048576',
    },
    'client': {
        'role': 'admin'
    },
    'filesystem': {
        'extensions_dir': '/usr/lib/pulp/admin/extensions',
        'id_cert_dir': '~/.pulp',
        'id_cert_filename': 'user-cert.pem',
        'upload_working_dir': '~/.pulp/uploads',
    },
    'logging': {
        'filename': '~/.pulp/admin.log',
        'call_log_filename': '~/.pulp/server_calls.log',
    },
    'output': {
        'poll_frequency_in_seconds': '1',
        'enable_color': 'true',
        'wrap_to_terminal': 'false',
        'wrap_width': '80',
    },
}


SCHEMA = (
    ('server', REQUIRED,
        (
            ('host', REQUIRED, ANY),
            ('port', REQUIRED, NUMBER),
            ('api_prefix', REQUIRED, ANY),
            ('verify_ssl', REQUIRED, BOOL),
            ('ca_path', REQUIRED, ANY),
            ('upload_chunk_size', REQUIRED, NUMBER),
        )
    ),
    ('client', REQUIRED,
        (
            ('role', REQUIRED, r'admin'),
        )
    ),
    ('filesystem', REQUIRED,
        (
            ('extensions_dir', REQUIRED, ANY),
            ('id_cert_dir', REQUIRED, ANY),
            ('id_cert_filename', REQUIRED, ANY),
            ('upload_working_dir', REQUIRED, ANY),
        )
    ),
    ('logging', REQUIRED,
        (
            ('filename', REQUIRED, ANY),
            ('call_log_filename', OPTIONAL, ANY)
        )
    ),
    ('output', REQUIRED,
        (
            ('poll_frequency_in_seconds', REQUIRED, NUMBER),
            ('enable_color', REQUIRED, BOOL),
            ('wrap_to_terminal', REQUIRED, BOOL),
            ('wrap_width', REQUIRED, NUMBER)
        )
    ),
)


def read_config(paths=None, validate=True):
    """
    Read and validate the admin configuration.
    :param validate: Validate the configuration.
    :param validate: bool
    :param paths: A list of paths to configuration files to read.
        Reads the standard locations when not specified.
    :param paths: list
    :return: A configuration object.
    :rtype: Config
    """
    if not paths:
        paths = ['/etc/pulp/admin/admin.conf']
        conf_d_dir = '/etc/pulp/admin/conf.d'
        paths += [os.path.join(conf_d_dir, i) for i in sorted(os.listdir(conf_d_dir))]
        overrides = os.path.expanduser('~/.pulp/admin.conf')
        if os.path.exists(overrides):
            paths.append(overrides)
    config = Config(DEFAULT)
    config.update(Config(*paths))
    if validate:
        config.validate(SCHEMA)
    return config