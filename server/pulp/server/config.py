import os
import socket
from ConfigParser import SafeConfigParser


config = None  # ConfigParser.SafeConfigParser instance

# to guarantee that a section and/or setting exists, add a default value here
_default_values = {
    'authentication': {
        'rsa_key': '/etc/pki/pulp/rsa.key',
        'rsa_pub': '/etc/pki/pulp/rsa_pub.key',
    },
    'consumer_history': {
        'lifetime': '180',  # in days
    },
    'data_reaping': {
        'reaper_interval': '0.25',
        'archived_calls': '0.5',
        'consumer_history': '60',
        'repo_sync_history': '60',
        'repo_publish_history': '60',
        'repo_group_publish_history': '60',
        'task_status_history': '7',
        'task_result_history': '3',
    },
    'database': {
        'name': 'pulp_database',
        'seeds': 'localhost:27017',
        'username': '',
        'password': '',
        'ssl': 'false',
        'ssl_keyfile': '',
        'ssl_certfile': '',
        'verify_ssl': 'true',
        'ca_path': '/etc/pki/tls/certs/ca-bundle.crt',
    },
    'email': {
        'host': 'localhost',
        'port': '25',
        'enabled': 'false',
        'from': 'pulp@localhost',
    },
    'oauth': {
        'enabled': 'true',
        'oauth_key': '',
        'oauth_secret': '',
    },
    'ldap': {
        'enabled': 'false',
        'uri': 'ldap://localhost',
        'base': 'dc=localhost',
        'tls': 'false',
    },
    'messaging': {
        'url': 'tcp://localhost:5672',
        'transport': 'qpid',
        'auth_enabled': 'true',
        'cacert': '/etc/pki/qpid/ca/ca.crt',
        'clientcert': '/etc/pki/qpid/client/client.pem',
        'topic_exchange': 'amq.topic'
    },
    'security': {
        'cacert': '/etc/pki/pulp/ca.crt',
        'cakey': '/etc/pki/pulp/ca.key',
        'ssl_ca_certificate': '/etc/pki/pulp/ssl_ca.crt',
        'user_cert_expiration': '7',
        'consumer_cert_expiration': '3650',
        'serial_number_path': '/var/lib/pulp/sn.dat',
    },
    'server': {
        'server_name': socket.gethostname(),
        'default_login': 'admin',
        'default_password': 'admin',
        'debugging_mode': 'false',
        'storage_dir': '/var/lib/pulp/',
        'log_level': 'INFO',
        'key_url': '/pulp/gpg',
        'ks_url': '/pulp/ks',
    },
    'tasks': {
        'broker_url': 'qpid://guest@localhost/',
        'celery_require_ssl': 'false',
        'cacert': '/etc/pki/pulp/qpid/ca.crt',
        'keyfile': '/etc/pki/pulp/qpid/client.crt',
        'certfile': '/etc/pki/pulp/qpid/client.crt',
    },
}

# to add a default configuration file, list the full path here
_config_files = ['/etc/pulp/server.conf']


def check_config_files():
    """
    Check for read permissions on the configuration files. Raise a runtime error
    if the file doesn't exist or the read permissions are lacking.
    """
    for config_file in _config_files:
        if not os.access(config_file, os.F_OK):
            raise RuntimeError('Cannot find configuration file: %s' % config_file)
        if not os.access(config_file, os.R_OK):
            raise RuntimeError('Cannot read configuration file: %s' % config_file)


def load_configuration():
    """
    Check the configuration files and load the global 'config' object from them.
    """
    global config
    check_config_files()
    config = SafeConfigParser()
    # add the defaults first
    for section, settings in _default_values.items():
        config.add_section(section)
        for option, value in settings.items():
            config.set(section, option, value)
    # read the config files
    return config.read(_config_files)


def add_config_file(file_path):
    """
    Convenience function to add a new file to the list of configuration files,
    then re-load the global config and re-configure logging.

    @type file_path: str
    @param file_path: full path to the new file to add
    """
    global _config_files
    if file_path in _config_files:
        raise RuntimeError('File, %s, already in configuration files' % file_path)
    _config_files.append(file_path)
    load_configuration()


def remove_config_file(file_path):
    """
    Convenience function to remove a file from the list of configuration files,
    then re-load the global config and re-configure logging.

    @type file_path: str
    @param file_path: full path to the file to remove
    """
    global _config_files
    if file_path not in _config_files:
        raise RuntimeError('File, %s, not in configuration files' % file_path)
    _config_files.remove(file_path)
    load_configuration()


load_configuration()
