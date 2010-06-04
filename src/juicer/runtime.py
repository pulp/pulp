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

__author__ = 'Jason L Connor <jconnor@redhat.com>'

"""
This module contains various globals that get set at runtime.
CONFIG - the raw configurations of juicer and pulp as a configuration parser
"""

import logging

CONFIG = None


def bootstrap(config):
    # the global CONFIG must be set *before* the application is imported
    global CONFIG
    CONFIG = config
    from juicer.application import wsgi_application

    format = logging.Formatter('%(asctime)s  %(message)s')

    file_handler = logging.FileHandler('/var/log/pulp/pulp-grinder.log')
    file_handler.setFormatter(format)
    logging.getLogger('grinder').addHandler(file_handler)
    logging.getLogger('grinder').setLevel(logging.DEBUG)

    file_handler = logging.FileHandler('/var/log/pulp/pulp.log')
    file_handler.setFormatter(format)
    logging.getLogger('pulp').addHandler(file_handler)
    logging.getLogger('pulp').setLevel(logging.DEBUG)

    return wsgi_application(config)
