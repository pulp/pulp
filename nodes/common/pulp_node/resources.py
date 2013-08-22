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

import os
import socket

from pulp.common.config import Config, REQUIRED, OPTIONAL, NUMBER, ANY
from pulp.common.bundle import Bundle
from pulp.bindings.server import PulpConnection
from pulp.bindings.bindings import Bindings


# --- constants --------------------------------------------------------------

NODE_CONFIGURATION_PATH = '/etc/pulp/nodes.conf'
SERVER_CONFIGURATION_PATH = '/etc/pulp/server.conf'
CONSUMER_CONFIGURATION_PATH = '/etc/pulp/consumer/consumer.conf'

NODE_SCHEMA = (
    ('main', REQUIRED,
        (
            ('node_id', REQUIRED, ANY),
            ('node_cert', REQUIRED, ANY),
        )
    ),
    ('oauth', REQUIRED,
        (
            ('host', OPTIONAL, ANY),
            ('port', OPTIONAL, NUMBER),
            ('key', OPTIONAL, ANY),
            ('secret', OPTIONAL, ANY),
            ('user_id', REQUIRED, ANY),
        )
    ),
    ('parent_oauth', REQUIRED,
        (
            ('host', REQUIRED, ANY),
            ('port', REQUIRED, NUMBER),
            ('key', REQUIRED, ANY),
            ('secret', REQUIRED, ANY),
            ('user_id', REQUIRED, ANY),
        )
    ),
)


# --- configuration ----------------------------------------------------------

def node_id():
    """
    Get the node ID.
    :return: The node ID.
    :rtype: str
    """
    node_conf = node_configuration()
    return node_conf.main.node_id


def node_configuration(path=NODE_CONFIGURATION_PATH):
    """
    Get the node configuration object.
    The node configuration is defaulted using values from the pulp consumer
    configuration and certificate when installed.
    :param path: The optional path to the configuration.
    :return: The configuration object.
    :rtype: pulp.common.config.Graph
    """
    node_conf = Config(path)
    conf_path = CONSUMER_CONFIGURATION_PATH
    if os.path.exists(path):
        conf = Config(conf_path)
        conf = conf.graph()
        host = conf.server.host
        port = conf.server.port
        cert_path = os.path.join(
            conf.filesystem.id_cert_dir, conf.filesystem.id_cert_filename)
        cert = Bundle(cert_path)
        node_id = cert.cn()
        node_conf.update(dict(main=dict(node_id=node_id)))
        node_conf.update(dict(parent_oauth=dict(host=host, port=port)))
    node_conf.validate(NODE_SCHEMA)
    return node_conf.graph()


def pulp_configuration(path=SERVER_CONFIGURATION_PATH):
    """
    Get the pulp server configuration object.
    :param path: The optional path to the configuration.
    :return: The configuration object.
    :rtype: pulp.common.config.Graph
    """
    conf = Config(path)
    return conf.graph()


# --- pulp bindings ----------------------------------------------------------

def parent_bindings():
    """
    Get a pulp bindings object for the parent node.
    :return: A pulp bindings object.
    :rtype: Bindings
    """
    node_conf = node_configuration()
    oauth = node_conf.parent_oauth
    connection = PulpConnection(
        host=oauth.host,
        port=int(oauth.port),
        oauth_key=oauth.key,
        oauth_secret=oauth.secret,
        oauth_user=oauth.user_id)
    return Bindings(connection)


def pulp_bindings():
    """
    Get a pulp bindings object for this node.
    Properties defined in the pulp server configuration are used
    when not defined in the node configuration.
    :return: A pulp bindings object.
    :rtype: Bindings
    """
    pulp_conf = pulp_configuration()
    node_conf = node_configuration()
    oauth = node_conf.oauth
    host = oauth.host or pulp_conf.server.host or socket.gethostname()
    connection = PulpConnection(
        host=host,
        port=int(oauth.port),
        oauth_key=node_conf.oauth.key or pulp_conf.oauth.oauth_key,
        oauth_secret=oauth.secret or pulp_conf.oauth.oauth_secret,
        oauth_user=node_conf.oauth.user_id)
    return Bindings(connection)