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

import os
from optparse import OptionParser, SUPPRESS_HELP

from pulp.server.config import config
from pulp.server.db.migrate.one import One
from pulp.server.db.version import current_data_model_version, get_version_from_db


def parse_args():
    parser = OptionParser()
    parser.add_option('--auto', action='store_true', dest='auto',
                      default=False, help=SUPPRESS_HELP)
    options, args = parser.parse_args()
    if args:
        parser.error('unknown arguments: %s' % ', '.join(args))
    return options


def main():
    options = parse_args()
    if options.auto and not config.getboolean('database', 'auto_upgrade'):
        return os.EX_CONFIG
    database_version = get_version_from_db()
    if database_version == current_data_model_version:
        return os.EX_USAGE
    if database_version is None:
        updater = One()
        updater.migrate()
        updater.validate()
        updater.set_version()
        return os.EX_OK
    return os.EX_SOFTWARE
