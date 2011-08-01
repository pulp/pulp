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

from pulp.client.lib.config import Config

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
    FILE = "consumer.conf"
    ALT = "PULP_CLIENT_OVERRIDE"
