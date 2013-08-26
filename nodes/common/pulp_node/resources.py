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

from pulp.common.config import Config, REQUIRED, ANY
from pulp.server.config import config as pulp_conf
from pulp.bindings.server import PulpConnection
from pulp.bindings.bindings import Bindings


# --- constants --------------------------------------------------------------

NODE_CONFIGURATION_PATH = '/etc/pulp/nodes.conf'
CONSUMER_CONFIGURATION_PATH = '/etc/pulp/consumer/consumer.conf'

NODE_SCHEMA = (
    ('oauth', REQUIRED,
        (
            ('user_id', REQUIRED, ANY),
        )
    ),
    ('parent_oauth', REQUIRED,
        (
            ('key', REQUIRED, ANY),
            ('secret', REQUIRED, ANY),
            ('user_id', REQUIRED, ANY),
        )
    ),
)


# --- configuration ----------------------------------------------------------

def node_configuration(path=NODE_CONFIGURATION_PATH):
    """
    Get the node configuration object.
    The node configuration is overridden using values from the pulp
    consumer.conf and defaulted using server.conf as appropriate.
    :param path: The optional path to the configuration.
    :return: The configuration object.
    :rtype: pulp.common.config.Graph
    """
    cfg = Config(path)
    cfg.validate(NODE_SCHEMA)
    return cfg.graph()


# --- pulp bindings ----------------------------------------------------------

def parent_bindings(host, port=443):
    """
    Get a pulp bindings object for the parent node.
    :return: A pulp bindings object.
    :rtype: Bindings
    """
    node_conf = node_configuration()
    oauth = node_conf.parent_oauth
    connection = PulpConnection(
        host=host,
        port=port,
        oauth_key=oauth.key,
        oauth_secret=oauth.secret,
        oauth_user=oauth.user_id)
    bindings = Bindings(connection)
    return bindings


def pulp_bindings():
    """
    Get a pulp bindings object for this node.
    Properties defined in the pulp server configuration are used
    when not defined in the node configuration.
    :return: A pulp bindings object.
    :rtype: Bindings
    """
    node_conf = node_configuration()
    oauth = node_conf.oauth
    host = pulp_conf.get('server', 'server_name'),
    key = pulp_conf.get('oauth', 'oauth_key'),
    secret = pulp_conf.get('oauth', 'oauth_secret'),
    connection = PulpConnection(
        host=host,
        port=443,
        oauth_key=key,
        oauth_secret=secret,
        oauth_user=oauth.user_id)
    bindings = Bindings(connection)
    return bindings