# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
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
from ConfigParser import SafeConfigParser

# global configuration --------------------------------------------------------

config = None # ConfigParser.SafeConfigParser instance

# to guarantee that a section and/or setting exists, add a default value here
_default_values = {
    'cds': {
        'sync_timeout': '10:7200',
    },
    'consumer_history': {
        'lifetime': '180', # in days
    },
    'coordinator': {
        'task_state_poll_interval': '0.1',
    },
    'database': {
        'auto_migrate': 'false',
        'name': 'pulp_database',
        'seeds': 'localhost:27017',
        'operation_retries': '2',
    },
    'email': {
        'host': 'localhost',
        'port': '25',
        'enabled' : 'false'
    },
    'events': {
        'send_enabled': 'false',
        'recv_enabled': 'false',
    },
    # XXX should 'ldap' be in here or not?
    'logs': {
        'config': '/etc/pulp/logging/basic.cfg',
        # XXX are the rest of these even used?
        'qpid_log_level': 'info',
        'level': 'info',
        'max_size': '1048576',
        'backups': '4',
        'pulp_file': '/var/log/pulp/pulp.log',
        'grinder_file': '/var/log/pulp/grinder.log',
    },
    'messaging': {
        'url': 'tcp://localhost:5672',
        'cacert': '/etc/pki/qpid/ca/ca.crt',
        'clientcert': '/etc/pki/qpid/client/client.pem',
    },
    'scheduler': {
        'dispatch_interval': '30',
    },
    'security': {
        'cacert': '/etc/pki/pulp/ca.crt',
        'cakey': '/etc/pki/pulp/ca.key',
        'ssl_ca_certificate' : '/etc/pki/pulp/ssl_ca.crt',
        # XXX should these be in here?
        #'oauth_key': '',
        #'oauth_secret': '',
        'user_cert_expiration': '7',
        'consumer_cert_expiration': '3650',
        'serial_number_path': '/var/lib/pulp/sn.dat',
    },
    'server': {
        'server_name': 'localhost',
        'relative_url': '/pulp/repos',
        'key_url': '/pulp/gpg',
        'ks_url' : '/pulp/ks',
        'default_login': 'admin',
        'default_password': 'admin',
        'debugging_mode': 'false',
        'storage_dir': '/var/lib/pulp/',
    },
    'tasks': {
        'concurrency_threshold': '9',
        'dispatch_interval': '0.5',
        'archived_call_lifetime': '48',
        'consumer_content_weight': '0',
        'create_weight': '0',
        'publish_weight': '1',
        'sync_weight': '2',
    },
}

# to add a default configuration file, list the full path here
_config_files = ['/etc/pulp/server.conf']

# configuration api -----------------------------------------------------------

def check_config_files():
    """
    Check for read permissions on the configuration files. Raise a runtime error
    if the file doesn't exist or the read permissions are lacking.
    """
    for file in _config_files:
        if not os.access(file, os.F_OK):
            raise RuntimeError('Cannot find configuration file: %s' % file)
        if not os.access(file, os.R_OK):
            raise RuntimeError('Cannot read configuration file: %s' % file)
    return 'Yeah!'


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

# ------------------------------------------------------------------------------

load_configuration()
