# -*- coding: utf-8 -*-

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
from optparse import OptionParser, SUPPRESS_HELP

from pulp.server.config import config
from pulp.server.db import connection
from pulp.server.db.migrate import one
from pulp.server.db.migrate.validate import validate
from pulp.server.db.version import (
    VERSION, get_version_in_use, is_validated, set_validated)


def parse_args():
    parser = OptionParser()
    parser.add_option('--auto', action='store_true', dest='auto',
                      default=False, help=SUPPRESS_HELP)
    parser.add_option('--log-file', dest='log_file',
                      default='/var/log/pulp/db.log',
                      help='file for log messages')
    parser.add_option('--log-level', dest='log_level', default='info',
                      help='level of logging (debug, info, error, critical)')
    options, args = parser.parse_args()
    if args:
        parser.error('unknown arguments: %s' % ', '.join(args))
    return options


def start_logging(options):
    level = getattr(logging, options.log_level.upper(), logging.INFO)
    logger = logging.getLogger('pulp') # imitate the pulp log handler
    logger.setLevel(level)
    handler = logging.FileHandler(options.log_file)
    logger.addHandler(handler)


def migrate_to_one():
    one.migrate()
    one.set_version()


def main():
    options = parse_args()
    start_logging(options)
    connection.initialize()
    if options.auto and not config.getboolean('database', 'auto_upgrade'):
        print >> sys.stderr, 'pulp is not configured for auto upgrade'
        return os.EX_CONFIG
    version = get_version_in_use()
    if version == VERSION:
        print 'data model in use matches the current version'
    while version < VERSION:
        # ADD MIGRATION CALLS HERE
        if version is None:
            migrate_to_one()
        version = get_version_in_use()
    errors = 0
    if not is_validated():
        errors = validate()
    if errors:
        print >> sys.stderr, '%d errors on validation, see %s for details' % \
                (errors, options.log_file)
        return os.EX_DATAERR
    set_validated()
    print 'database migration to version %d complete' % VERSION
    return os.EX_OK
