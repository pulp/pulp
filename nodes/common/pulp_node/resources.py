from pulp.common.config import parse_bool
from pulp.server.config import config as pulp_conf
from pulp.bindings.server import PulpConnection
from pulp.bindings.bindings import Bindings

from pulp_node.config import read_config


def parent_bindings(host, port=443):
    """
    Get a pulp bindings object for the parent node.
    :param host: The hostname of IP of the parent server.
    :type host: str
    :param port: The TCP port number.
    :type port: int
    :return: A pulp bindings object.
    :rtype: Bindings
    """
    node_conf = read_config()
    oauth = node_conf.parent_oauth
    verify_ssl = parse_bool(node_conf.main.verify_ssl)
    ca_path = node_conf.main.ca_path
    connection = PulpConnection(
        host=host,
        port=port,
        oauth_key=oauth.key,
        oauth_secret=oauth.secret,
        oauth_user=oauth.user_id,
        verify_ssl=verify_ssl,
        ca_path=ca_path)
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
    node_conf = read_config()
    oauth = node_conf.oauth
    verify_ssl = parse_bool(node_conf.main.verify_ssl)
    ca_path = node_conf.main.ca_path
    host = pulp_conf.get('server', 'server_name')
    key = pulp_conf.get('oauth', 'oauth_key')
    secret = pulp_conf.get('oauth', 'oauth_secret')
    connection = PulpConnection(
        host=host,
        port=443,
        oauth_key=key,
        oauth_secret=secret,
        oauth_user=oauth.user_id,
        verify_ssl=verify_ssl,
        ca_path=ca_path)
    bindings = Bindings(connection)
    return bindings
