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

import logging
import logging.config
import os
import sys
from logging import handlers

from pulp.server import config


TIME = '%(asctime)s'
LEVEL = ' [%(levelname)s]'
THREAD = '[%(threadName)s]'
FUNCTION = ' %(funcName)s()'
FILE = ' @ %(filename)s'
LINE = ':%(lineno)d'
MSG = ' - %(message)s'

if sys.version_info < (2,5):
    FUNCTION = ''

FMT = \
    ''.join((TIME,
            LEVEL,
            THREAD,
            FUNCTION,
            FILE,
            LINE,
            MSG,))


# logging configuration -------------------------------------------------------

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

def _enable_all_loggers():
    """
    This is a workaround needed for python 2.4
    python 2.4 will disable all existing loggers if the 'qualname' does not match
    exactly to the logger name.  This means that pulp.server.api.repo_sync will be disabled
    for the common case of only have a logger configured for 'pulp'

    Newer versions of python address this issue when this patch is present;
    http://bugs.python.org/issue3136
    we could just pass in a 'disable_existing_loggers=False'
    """
    keys = logging.root.manager.loggerDict.keys()
    for key in keys:
        logging.root.manager.loggerDict[key].disabled = 0

def configure_pulp_logging():
    """
    Configures logging from config file specified in pulp.conf
    """
    log_config_filename = config.config.get('logs', 'config')
    if not os.access(log_config_filename, os.R_OK):
        raise RuntimeError("Unable to read log configuration file: %s" % (log_config_filename))
    logging.config.fileConfig(log_config_filename)
    _enable_all_loggers() # Hack needed for RHEL-5

def configure_audit_logging():
    """
    Pull the audit logging configuration from the global config and/or default
    config and initialize pulp's audit logging.
    """
    file = config.config.get('auditing', 'events_file')
    check_log_file(file)
    units = 'D'
    backups = config.config.getint('auditing', 'backups')
    lifetime = config.config.getint('auditing', 'lifetime')

    # the logging module will get into an infinite loop if the interval is 0
    if lifetime <= 0:
        units = 'H'
        lifetime = 1

    # NOTE, this cannot be a descendant of the pulp log as it will inherit
    # pulp's rotating log and handler and log to both files. Yes, I've tried
    # removing the handler to no avail...
    logger = logging.getLogger('auditing')
    logger.setLevel(logging.INFO)
    logger.propagate = 0 # Disables auditing going to regular log output
    handler = handlers.TimedRotatingFileHandler(file,
                                                when=units,
                                                interval=lifetime,
                                                backupCount=backups)
    logger.addHandler(handler)

# pulp logging api ------------------------------------------------------------

started = False

def start_logging():
    """
    Convenience function to start pulp's different logging mechanisms.
    """
    assert config.config is not None
    global started
    if started:
        return
    configure_pulp_logging()
    configure_audit_logging()
    started = True


def stop_logging():
    """
    Convenience function to stop pulp's different logging mechanisms.
    """
    global started
    if not started:
        return
    # remove all the existing handlers and loggers from the logging module
    logging.shutdown()
    logging.Logger.manager.loggerDict = {} # ew
    started = False


def restart_logging():
    """
    Convenience function to restart pulp's different logging mechanisms.
    """
    stop_logging()
    start_logging()
