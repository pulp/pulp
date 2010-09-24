#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import os
from ConfigParser import SafeConfigParser

# global configuration --------------------------------------------------------

config = None # ConfigParser.SafeConfigParser instance

# to guarantee that a section and/or setting exists, add a default value here
_default_values = {
    'auditing': {
        'events_file': '/var/log/pulp/events.log',
        'lifetime': '90',
        'backups': '4',
    },
    'consumer_history': {
        'lifetime': '180', # in days
    },
    'logs': {
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
    'paths': {
        'local_storage': '/var/lib/pulp',
    },
    'repos': {
        'content_url': 'https://cdn.redhat.com/',
        'content_cert_location': '/etc/pki/content',
        'use_entitlement_certs': 'false',
    },
    'rhn': {
        'threads': '10',
        'fetch_all_packages': 'false',
        'remove_old_packages': 'false',
        'cert_file': '/etc/sysconfig/rhn/entitlement-cert.xml',
        'systemid_file': '/etc/sysconfig/rhn/systemid',
    },
    'security': {
        'cacert': '/etc/pki/pulp/ca.crt',
        'cakey': '/etc/pki/pulp/ca.key',
    },
    'server': {
        'base_url': 'http://localhost',
        'relative_url': '/pub',
        'default_login': 'admin',
        'default_password': 'admin',
    },
    'yum': {
        'threads': '10',
    },
}

# to add a default configuration file, list the full path here
_config_files = ['/etc/pulp/pulp.conf']

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

# initialize on import --------------------------------------------------------

load_configuration()
