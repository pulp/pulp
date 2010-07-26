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

import logging.handlers
import os.path
from ConfigParser import SafeConfigParser

# global configuration --------------------------------------------------------

config = None # ConfigParser.SafeConfigParser instance

default_values = {
    'logs': {
        'level': 'info',
        'max_size': '20480',
        'backups': '4',
        'pulp_file': '/var/log/pulp/pulp.log',
        'grinder_file': '/var/log/pulp/grinder.log',
    },
    'auditing': {
        'events_file': '/var/log/pulp/events.log',
        'lifetime': '365',
        'backups': '4',
    }
}

config_files = ['/etc/pulp/pulp.conf']

# configuration api -----------------------------------------------------------

def check_config_files():
    """
    Check for read permissions on the configuration files. Raise a runtime error
    if the file doesn't exist or the read permissions are lacking.
    """
    for file in config_files:
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
    return config.read(config_files)
        

def add_config_file(file_path):
    """
    Convenience function to add a new file to the list of configuration files,
    then re-load the global config and re-configure logging.
    
    @type file_path: str
    @param file_path: full path to the new file to add
    """
    global config_files
    if file_path in config_files:
        raise RuntimeError('File, %s, already in configuration files' % file_path)
    config_files.append(file_path)
    files = load_configuration()
    configure_logging()
    log_configuration(files)
    

def remove_config_file(file_path):
    """
    Convenience function to remove a file from the list of configuration files,
    then re-load the global config and re-configure logging.
    
    @type file_path: str
    @param file_path: full path to the file to remove
    """
    global config_files
    if file_path not in config_files:
        raise RuntimeError('File, %s, not in configuration files' % file_path)
    config_files.remove(file_path)
    files = load_configuration()
    configure_logging()
    log_configuration(files)
    
    
def log_configuration(files):
    """
    Log the list of configuration files that were successfully read.
    
    @type fiels: list or tuple
    @param files: list of configuration files that were read
    """
    log = logging.getLogger('pulp.config')
    log.info('Successfully loaded configuration from: %s' % ', '.join(files))

# logging configuration api ---------------------------------------------------

def check_log_file(file_path):
    """
    Check the write permissions on log files and their parent directory. Raise
    a runtime error if the write permissions are lacking.
    """
    if os.path.exists(file_path) and not os.access(file_path, os.W_OK):
        raise RuntimeError('Cannot write to log file: %s' % file_path)
    dir_path = os.path.dirname(file_path)
    if not os.access(dir_path, os.W_OK):
        raise RuntimeError('Cannot write to log directory: %s' % dir_path)
    return 'Yeah!'


def configure_pulp_grinder_logging():
    """
    Pull the log file configurations from the global config and/or default
    config and initialize the top-level logging for both pulp and grinder.
    """
    default_config = default_values['logs']
    log_config = {}
    if config.has_section('logs'):
        log_config = dict(config.items('logs'))
        
    level_name = log_config.get('level', default_config['level']).upper()
    level = getattr(logging, level_name, logging.INFO)
    max_size = int(log_config.get('max_size', default_config['max_size']))
    backups = int(log_config.get('backups', default_config['backups']))
    
    formatter = logging.Formatter('%(asctime)s  %(message)s')
    
    pulp_file = log_config.get('pulp_file', default_config['pulp_file'])
    check_log_file(pulp_file)
    pulp_logger = logging.getLogger('pulp')
    pulp_logger.setLevel(level)
    pulp_handler = logging.handlers.RotatingFileHandler(pulp_file,
                                                        maxBytes=max_size,
                                                        backupCount=backups)
    pulp_handler.setFormatter(formatter)
    pulp_logger.addHandler(pulp_handler)
    
    grinder_file = log_config.get('grinder_file', default_config['grinder_file'])
    check_log_file(grinder_file)
    grinder_logger = logging.getLogger('grinder')
    grinder_logger.setLevel(level)
    grinder_handler = logging.handlers.RotatingFileHandler(grinder_file,
                                                           maxBytes=max_size,
                                                           backupCount=backups)
    grinder_handler.setFormatter(formatter)
    grinder_logger.addHandler(grinder_handler)
    
    
def configure_audit_logging():
    """
    Pull the audit logging configuration from the global config and/or default
    config and initialize pulp's audit logging.
    """
    default_config = default_values['auditing']
    audit_config = {}
    if config.has_section('auditing'):
        audit_config = dict(config.items('auditing'))
        
    file = audit_config.get('events_file', default_config['events_file'])
    check_log_file(file)
    lifetime = int(audit_config.get('lifetime', default_config['lifetime']))
    backups = int(audit_config.get('backups', default_config['backups']))
    
    logger = logging.getLogger('pulp.auditing')
    logger.setLevel(logging.INFO)
    handler = logging.handlers.TimedRotatingFileHandler(file,
                                                        when='D',
                                                        interval=lifetime,
                                                        backupCount=backups)
    logger.addHandler(handler)
    
    
def configure_logging():
    """
    Convenience function to initialize pulp's different logging mechanisms.
    """
    configure_pulp_grinder_logging()
    configure_audit_logging()

# bootstrap -------------------------------------------------------------------

files = load_configuration()    
configure_logging()
log_configuration(files)
