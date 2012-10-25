# Copyright (c) 2010-2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from gettext import lgettext as _
from optparse import OptionParser, SUPPRESS_HELP
import logging
import traceback
import os
import sys

from pulp.plugins.loader.api import load_content_types
from pulp.server.db import connection
from pulp.server.db.migrate import utils

connection.initialize()

_log = logging.getLogger('pulp')


class DataError(Exception):
    """
    This Exception is used when we want to return the os.EX_DATAERR code.
    """
    pass


def parse_args():
    parser = OptionParser()
    parser.add_option('--force', action='store_true', dest='force',
                      default=False, help=SUPPRESS_HELP)
    parser.add_option('--from', dest='start', default=None,
                      help=_('Run the migration starting at the version passed in'))
    parser.add_option('--test', action='store_true', dest='test',
                      default=False,
                      help=_('Run migration, but do not update version'))
    parser.add_option('--log-file', dest='log_file',
                      default='/var/log/pulp/db.log',
                      help=_('File for log messages'))
    parser.add_option('--log-level', dest='log_level', default='info',
                      help=_('Level of logging (debug, info, error, critical)'))
    options, args = parser.parse_args()
    if args:
        parser.error(_('Unknown arguments: %s') % ', '.join(args))
    return options


def start_logging(options):
    level = getattr(logging, options.log_level.upper(), logging.INFO)
    logger = logging.getLogger('pulp') # imitate the pulp log handler
    logger.setLevel(level)
    handler = logging.FileHandler(options.log_file)
    logger.addHandler(handler)


def migrate_database(options):
    """
    Perform the migrations for each migration package found in pulp.server.db.migrations.

    :param options: The command line parameters from the user
    """
    migration_packages = utils.get_migration_packages()
    for migration_package in migration_packages:
        if migration_package.current_version > migration_package.latest_available_version:
            raise DataError(_('The database for migration package %(p)s is at version %(v)s, ' +\
                              'which is larger than the latest version available, %(a)s.')%({
                                'p': migration_package.name, 'v': migration_package.current_version,
                                'a': migration_package.latest_available_version}))
        if migration_package.current_version == migration_package.latest_available_version:
            print _('Migration package %(p)s is up to date at version %(v)s'%({
                'p': migration_package.name,
                'v': migration_package.latest_available_version}))
            continue

        try:
            for migration in migration_package.unapplied_migrations:
                print _('Applying %(p)s version %(v)s'%({
                    'p': migration_package.name, 'v': migration.version}))
                migration_package.apply_migration(migration)
                print _('Migration to %(p)s version %(v)s complete.'%(
                    {'p': migration_package.name, 'v': migration_package.current_version}))
        except Exception, e:
            # If an Exception is raised while applying the migrations, we should log and print it,
            # and then continue with the other packages.
            error_message = _('Applying migration %(m)s failed.')%(
                              {'m': migration.name})
            print >> sys.stderr, str(error_message), _(' See log for details.')
            _log.critical(error_message)
            _log.critical(str(e))
            _log.critical(''.join(traceback.format_exception(*sys.exc_info())))


def main():
    try:
        options = parse_args()
        start_logging(options)
        _auto_manage_db(options)
    except DataError, e:
        _log.critical(str(e))
        _log.critical(''.join(traceback.format_exception(*sys.exc_info())))
        print >> sys.stderr, str(e)
        return os.EX_DATAERR
    except Exception, e:
        _log.critical(str(e))
        _log.critical(''.join(traceback.format_exception(*sys.exc_info())))
        print >> sys.stderr, str(e)
        return os.EX_SOFTWARE


def _auto_manage_db(options):
    """
    Find and apply all available database migrations, and install or update all available content
    types.

    :param options: The command line parameters from the user.
    """
    if options.force:
        print _('Clearing previous versions.')
        clean_db()

    if options.start is not None:
        last = int(options.start) - 1
        print _('Reverting db to version %(v)d.') % ({'v': last},)
        revert_to_version(last)

    print _('Beginning database migrations.')
    migrate_database(options)
    print _('Database migrations complete.')

    print _('Loading content types.')
    load_content_types()
    print _('Content types loaded.')
    return os.EX_OK
