from gettext import gettext as _
import os
import socket

from pulp.common.config import Config, REQUIRED, ANY, NUMBER, BOOL, OPTIONAL

DEFAULT = {
    'server': {
        'host': socket.gethostname(),
        'port': '443',
        'api_prefix': '/pulp/api',
        'verify_ssl': 'true',
        'ca_path': '/etc/pki/tls/certs/ca-bundle.crt',
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
            validate_overrides(overrides)
            paths.append(overrides)
    config = Config(DEFAULT)
    config.update(Config(*paths))
    if validate:
        config.validate(SCHEMA)
    return config


def validate_overrides(path):
    """
    Raise RuntimeError if the file at 'path' provides a password and is not private to owner.

    :param path: Full path to the file to check. Assumed the file exists.
    :type path: basestring

    :raises: RuntimeError if file is not private and contains a password
    """
    valid_private_perms = [400, 600, 700]
    file_perm = int(oct(os.stat(path).st_mode & 0777))

    cfg = Config(path)
    if cfg.has_option("auth", "password"):
        if file_perm not in valid_private_perms:
            runtime_dict = {'path': path, 'file_perm': file_perm,
                            'valid_private_perms': valid_private_perms}
            raise RuntimeError(_(
                "File %(path)s contains a password and has incorrect permissions: %(file_perm)d, "
                "It should be one of %(valid_private_perms)s.") % runtime_dict)
