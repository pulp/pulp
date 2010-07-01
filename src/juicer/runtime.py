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
"""
This module contains various globals that get set at runtime.
CONFIG - the raw configurations of juicer and pulp as a configuration parser
"""

import logging


config = None


def bootstrap(cfg):
    # the global CONFIG must be set *before* the application is imported
    global config
    config = cfg
    from juicer.application import wsgi_application

    # Logging
    LEVELS = {'debug':    logging.DEBUG,
              'info':     logging.INFO,
              'warning':  logging.WARNING,
              'error':    logging.ERROR,
              'critical': logging.CRITICAL}
    log_level = LEVELS[config.get('logs', 'level')]

    format = logging.Formatter('%(asctime)s  %(message)s')

    file_handler = logging.FileHandler(config.get('logs', 'grinder_file'))
    file_handler.setFormatter(format)
    logging.getLogger('grinder').addHandler(file_handler)
    logging.getLogger('grinder').setLevel(log_level)

    file_handler = logging.FileHandler(config.get('logs', 'pulp_file'))
    file_handler.setFormatter(format)
    logging.getLogger('pulp').addHandler(file_handler)
    logging.getLogger('pulp').setLevel(log_level)

    return wsgi_application(config)
