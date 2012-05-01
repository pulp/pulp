#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

from pulp.gc_client.lib.config import Config
from pulp.common.config import Validator
from pulp.common.config import ANY, NUMBER, BOOL, REQUIRED, OPTIONAL
from pulp.common.config import ValidationException

SCHEMA = (
    ('server', REQUIRED,
        (
            ('host', REQUIRED, ANY),
            ('port', REQUIRED, NUMBER),
            ('api_prefix', REQUIRED, ANY),
        )
    ),
    ('filesystem', REQUIRED,
        (
            ('extensions_dir', REQUIRED, ANY),
            ('repo_file', REQUIRED, ANY),
            ('mirror_list_dir', REQUIRED, ANY),
            ('gpg_keys_dir', REQUIRED, ANY),
            ('cert_dir', REQUIRED, ANY),
            ('consumer_cert', REQUIRED, ANY),
        )
    ),
    ('reboot', REQUIRED,
        (
            ('permit', REQUIRED, BOOL),
            ('delay', REQUIRED, NUMBER),
        )
    ),
)


class ConsumerConfig(Config):
    """
    The pulp consumer configuration.

    @cvar BASE_PATH: The absolute path to the config directory.
    @type BASE_PATH: str
    @cvar FILE: The name of the config file.
    @type FILE: str
    @cvar ALT: The environment variable with a path to an alternate
        configuration file.
    @type ALT: str
    """

    BASE_PATH = "/etc/pulp/consumer"
    FILE = "v2_consumer.conf"
    ALT = "PULP_CLIENT_OVERRIDE"

    def validate(self):
        """
        Validate configuration.
        """
        v = Validator(SCHEMA)
        try:
            return v.validate(self)
        except ValidationException, e:
            e.path = self.FILE_PATH
            raise e
