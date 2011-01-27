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

import logging
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


def configure_pulp_grinder_logging():
    """
    Pull the log file configurations from the global config and/or default
    config and initialize the top-level logging for both pulp and grinder.
    """
    level_name = config.config.get('logs', 'level').upper()
    level = getattr(logging, level_name, logging.INFO)
    max_size = config.config.getint('logs', 'max_size')
    backups = config.config.getint('logs', 'backups')
    formatter = logging.Formatter(FMT)

    #
    # Pulp (pulp, qpid, gopher)
    #
    pulp_file = config.config.get('logs', 'pulp_file')
    check_log_file(pulp_file)
    pulp_handler = handlers.RotatingFileHandler(pulp_file,
                                                maxBytes=max_size,
                                                backupCount=backups)
    pulp_handler.setFormatter(formatter)
    

    for pkg in ('pulp', 'gofer'):
        logger = logging.getLogger(pkg)
        logger.setLevel(level)
        logger.addHandler(pulp_handler)

    #
    # Qpid - qpid debug is very verbose, so break this out so we
    # we can enable pulp in debug and not be forced to have qpid in debug
    #
    qpid_level_name = config.config.get('logs', 'qpid_log_level').upper()
    qpid_level = getattr(logging, qpid_level_name, logging.INFO)
    logger = logging.getLogger('qpid')
    logger.setLevel(qpid_level)
    logger.addHandler(pulp_handler)

    #
    # Grinder
    #
    grinder_file = config.config.get('logs', 'grinder_file')
    check_log_file(grinder_file)
    grinder_logger = logging.getLogger('grinder')
    grinder_logger.setLevel(level)
    grinder_handler = handlers.RotatingFileHandler(grinder_file,
                                                   maxBytes=max_size,
                                                   backupCount=backups)
    grinder_handler.setFormatter(formatter)
    grinder_logger.addHandler(grinder_handler)


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
    configure_pulp_grinder_logging()
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
