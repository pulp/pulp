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

from pulp.common.config import Config, REQUIRED, ANY, NUMBER, BOOL, OPTIONAL


SCHEMA = (
    ('server', REQUIRED,
        (
            ('host', REQUIRED, ANY),
            ('port', REQUIRED, NUMBER),
            ('api_prefix', REQUIRED, ANY)
        )
    ),
    ('client', REQUIRED,
        (
            ('role', REQUIRED, ANY),
        )
    ),
    ('filesystem', REQUIRED,
        (
            ('extensions_dir', REQUIRED, ANY),
            ('repo_file', REQUIRED, ANY),
            ('mirror_list_dir', REQUIRED, ANY),
            ('gpg_keys_dir', REQUIRED, ANY),
            ('cert_dir', REQUIRED, ANY),
            ('id_cert_dir', REQUIRED, ANY),
            ('id_cert_filename', REQUIRED, ANY),
        )
    ),
    ('reboot', REQUIRED,
        (
            ('permit', REQUIRED, BOOL),
            ('delay', REQUIRED, NUMBER),
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
    ('messaging', REQUIRED,
        (
            ('scheme', REQUIRED, r'(tcp|ssl)'),
            ('host', OPTIONAL, ANY),
            ('port', REQUIRED, NUMBER),
            ('cacert', OPTIONAL, ANY),
            ('clientcert', OPTIONAL, ANY)
        )
    ),
    ('profile', REQUIRED,
        (
            ('minutes', REQUIRED, NUMBER),
        )
    ),
)


def read_config(paths=None, validate=True):
    """
    Read and validate the consumer configuration.
    :param validate: Validate the configuration.
    :param validate: bool
    :param paths: A list of paths to configuration files to read.
        Reads the standard locations when not specified.
    :param paths: list
    :return: A configuration object.
    :rtype: Config
    """
    if not paths:
        paths = ['/etc/pulp/consumer/consumer.conf']
        overrides = os.path.expanduser('~/.pulp/consumer.conf')
        if os.path.exists(overrides):
            paths.append(overrides)
    config = Config(*paths)
    if validate:
        config.validate(SCHEMA)
    return config