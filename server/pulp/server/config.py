import os
import socket
from ConfigParser import SafeConfigParser

from pulp.common.constants import DEFAULT_CA_PATH


class LazyConfigParser(SafeConfigParser):
    def __init__(self, *args, **kwargs):
        self.reload()
        SafeConfigParser.__init__(self, *args, **kwargs)

        # The superclass _sections attr takes precedence over the property of
        # the same name defined below. Deleting it exposes that property to hook
        # the config loading mechanism into an attribute used by just about every
        # ConfigParser method.
        self._lazy_sections = self._sections
        del self._sections

    def reload(self):
        self._loaded = False

    @property
    def _sections(self):
        self._load_config()
        return self._lazy_sections

    def _load_config(self):
        # calls to self.get/self.set access _sections, which triggers _load_config,
        # so to avoid infinite recursion _loaded is set before calling those methods
        if self._loaded:
            return
        self._loaded = True

        # add the defaults first
        self._sections.clear()
        for section, settings in _default_values.items():
            self.add_section(section)
            for option, value in settings.items():
                self.set(section, option, value)

        # check and load config files
        check_config_files()
        self.read(_config_files)


config = LazyConfigParser()

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
        'ca_path': DEFAULT_CA_PATH,
        'unsafe_autoretry': 'false',
        'write_concern': 'majority',
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
        'topic_exchange': 'amq.topic',
        'event_notifications_enabled': 'false',
        'event_notification_url': 'qpid://localhost:5672/',
    },
    'security': {
        'cacert': '/etc/pki/pulp/ca.crt',
        'cakey': '/etc/pki/pulp/ca.key',
        'ssl_ca_certificate': '/etc/pki/pulp/ssl_ca.crt',
        'user_cert_expiration': '7',
        'consumer_cert_expiration': '3650',
    },
    'server': {
        'server_name': socket.getfqdn(),
        'default_login': 'admin',
        'default_password': 'admin',
        'debugging_mode': 'false',
        'storage_dir': '/var/lib/pulp/',
        'log_level': 'INFO',
        'log_type': 'syslog',
        'key_url': '/pulp/gpg',
        'ks_url': '/pulp/ks',
        'working_directory': '/var/cache/pulp'
    },
    'tasks': {
        'broker_url': 'qpid://localhost/',
        'celery_require_ssl': 'false',
        'cacert': '/etc/pki/pulp/qpid/ca.crt',
        'keyfile': '/etc/pki/pulp/qpid/client.crt',
        'certfile': '/etc/pki/pulp/qpid/client.crt',
        'login_method': '',
        'worker_timeout': '30',
    },
    'lazy': {
        'redirect_host': '',
        'redirect_port': '',
        'redirect_path': '/streamer/',
        'https_retrieval': 'true',
        'download_interval': '30',
        'download_concurrency': '5'
    },
    'profiling': {
        'enabled': 'false',
        'directory': '/var/lib/pulp/c_profiles'
    }
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
    # config is lazy, so this doesn't immediately trigger a load
    # the actual load will occur the next time config is accessed
    config.reload()
    return config


def add_config_file(file_path):
    """
    Convenience function to add a new file to the list of configuration files,
    then re-load the global config and re-configure logging.

    @type file_path: str
    @param file_path: full path to the new file to add
    """
    if file_path in _config_files:
        raise RuntimeError('File, %s, already in configuration files' % file_path)
    _config_files.append(file_path)
    config.reload()


def remove_config_file(file_path):
    """
    Convenience function to remove a file from the list of configuration files,
    then re-load the global config and re-configure logging.

    @type file_path: str
    @param file_path: full path to the file to remove
    """
    if file_path not in _config_files:
        raise RuntimeError('File, %s, not in configuration files' % file_path)
    _config_files.remove(file_path)
    config.reload()
