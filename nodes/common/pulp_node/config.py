from pulp.common.config import ANY, BOOL, Config, REQUIRED


NODE_CONFIGURATION_PATH = '/etc/pulp/nodes.conf'

DEFAULT = {
    'main': {
        'ca_path': '/etc/pki/tls/certs/ca-bundle.crt',
        'node_certificate': '/etc/pki/pulp/nodes/node.crt',
        'verify_ssl': 'true',
    },
    'oauth': {
        'user_id': 'admin',
    },
    'parent_oauth': {
        'key': '',
        'secret': '',
        'user_id': 'admin',
    },
}

SCHEMA = (
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


def read_config(path=NODE_CONFIGURATION_PATH, validate=True):
    """
    Get the node configuration object.
    The node configuration is overridden using values from the pulp
    consumer.conf and defaulted using server.conf as appropriate.
    :param path: The optional path to the configuration.
    :return: The configuration object.
    :rtype: pulp.common.config.Graph
    """
    config = Config(DEFAULT)
    config.update(Config(path))
    if validate:
        config.validate(SCHEMA)
    return config.graph()