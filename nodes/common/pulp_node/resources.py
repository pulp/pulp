from pulp.common.config import ANY, BOOL, Config, REQUIRED, parse_bool
from pulp.server.config import config as pulp_conf
from pulp.bindings.server import PulpConnection
from pulp.bindings.bindings import Bindings


NODE_CONFIGURATION_PATH = '/etc/pulp/nodes.conf'
CONSUMER_CONFIGURATION_PATH = '/etc/pulp/consumer/consumer.conf'

NODE_SCHEMA = (
    ('main', REQUIRED,
        (
            ('ca_path', REQUIRED, ANY),
            ('node_certificate', REQUIRED, ANY),
            ('verify_ssl', REQUIRED, BOOL),
        )
    ),
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
    node_conf = node_configuration()
    oauth = node_conf.parent_oauth
    verify_ssl = parse_bool(node_conf.main.verify_ssl)
    ca_path = node_conf.main.ca_path
    connection = PulpConnection(
        host=host,
        port=port,
        oauth_key=oauth.key,
        oauth_secret=oauth.secret,
        oauth_user=oauth.user_id,
        validate_ssl_ca=verify_ssl,
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
    node_conf = node_configuration()
    oauth = node_conf.oauth
    verify_ssl = False if node_conf.main.verify_ssl.lower() == 'false' else True
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
        validate_ssl_ca=verify_ssl,
        ca_path=ca_path)
    bindings = Bindings(connection)
    return bindings
