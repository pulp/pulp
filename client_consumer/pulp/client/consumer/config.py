import os
import socket

from pulp.common.config import Config, REQUIRED, ANY, NUMBER, BOOL, OPTIONAL


DEFAULT = {
    'server': {
        'host': socket.gethostname(),
        'port': '443',
        'api_prefix': '/pulp/api',
        'rsa_pub': '/etc/pki/pulp/consumer/server/rsa_pub.key',
        'verify_ssl': 'true',
        'ca_path': '/etc/pki/tls/certs/ca-bundle.crt',
    },
    'authentication': {
        'rsa_key': '/etc/pki/pulp/consumer/rsa.key',
        'rsa_pub': '/etc/pki/pulp/consumer/rsa_pub.key'
    },
    'client': {
        'role': 'consumer'
    },
    'filesystem': {
        'extensions_dir': '/usr/lib/pulp/consumer/extensions',
        'repo_file': '/etc/yum.repos.d/pulp.repo',
        'mirror_list_dir': '/etc/yum.repos.d',
        'gpg_keys_dir': '/etc/pki/pulp-gpg-keys',
        'cert_dir': '/etc/pki/pulp/client/repo',
        'id_cert_dir': '/etc/pki/pulp/consumer/',
        'id_cert_filename': 'consumer-cert.pem',
    },
    'reboot': {
        'permit': 'false',
        'delay': '3',
    },
    'output': {
        'poll_frequency_in_seconds': '1',
        'enable_color': 'true',
        'wrap_to_terminal': 'false',
        'wrap_width': '80',
    },
    'messaging': {
        'scheme': 'amqp',
        'host': None,
        'port': '5672',
        'transport': 'qpid',
        'cacert': None,
        'clientcert': None,
    },
    'profile': {
        'minutes': '240',
    }
}


SCHEMA = (
    ('server', REQUIRED,
     (('host', REQUIRED, ANY),
      ('port', REQUIRED, NUMBER),
      ('api_prefix', REQUIRED, ANY),
      ('verify_ssl', REQUIRED, BOOL),
      ('ca_path', REQUIRED, ANY),
      ('rsa_pub', REQUIRED, ANY))),
    ('authentication', REQUIRED,
     (('rsa_key', REQUIRED, ANY),
      ('rsa_pub', REQUIRED, ANY))),
    ('client', REQUIRED,
     (('role', REQUIRED, r'consumer'),),),
    ('filesystem', REQUIRED,
     (('extensions_dir', REQUIRED, ANY),
      ('repo_file', REQUIRED, ANY),
      ('mirror_list_dir', REQUIRED, ANY),
      ('gpg_keys_dir', REQUIRED, ANY),
      ('cert_dir', REQUIRED, ANY),
      ('id_cert_dir', REQUIRED, ANY),
      ('id_cert_filename', REQUIRED, ANY))),
    ('reboot', REQUIRED,
     (('permit', REQUIRED, BOOL),
      ('delay', REQUIRED, NUMBER))),
    ('output', REQUIRED,
     (('poll_frequency_in_seconds', REQUIRED, NUMBER),
      ('enable_color', REQUIRED, BOOL),
      ('wrap_to_terminal', REQUIRED, BOOL),
      ('wrap_width', REQUIRED, NUMBER))),
    ('messaging', REQUIRED,
     (('scheme', REQUIRED, r'(tcp|ssl|amqp|amqps)'),
      ('host', OPTIONAL, ANY),
      ('port', REQUIRED, NUMBER),
      ('transport', REQUIRED, ANY),
      ('cacert', OPTIONAL, ANY),
      ('clientcert', OPTIONAL, ANY))),
    ('profile', REQUIRED,
     (('minutes', REQUIRED, NUMBER),)))


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
        conf_d_dir = '/etc/pulp/consumer/conf.d'
        paths += [os.path.join(conf_d_dir, i) for i in sorted(os.listdir(conf_d_dir))]
        overrides = os.path.expanduser('~/.pulp/consumer.conf')
        if os.path.exists(overrides):
            paths.append(overrides)
    config = Config(DEFAULT)
    config.update(Config(*paths))
    if validate:
        config.validate(SCHEMA)
    return config
