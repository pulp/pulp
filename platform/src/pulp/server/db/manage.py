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

# the db connection and auditing need to be initialied before any further
# imports since the imports execute initialization code relying on the
# db/auditing to be setup
connection.initialize()

_log = logging.getLogger('pulp')

from pulp.server.db.migrate.validate import validate
from pulp.server.db.migrate.versions import get_migration_modules
from pulp.server.db.model.migration_tracker import MigrationTracker


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
    migration_packages = utils.get_migration_packages()
    for migration_package in migration_packages:
        current_version = utils.get_current_package_version(migration_package)
        migrations = utils.get_migrations(migration_package)
        #If there are no migrations for this package, the latest version is 0
        latest_version = migrations[-1].version if migrations else 0

        if current_version is None:
            # This must be a new migration package that wasn't here before. We should create a new
            # DB object to track that we are at the latest version.
            print _('Found new migration package %s. Fast forwarding DB to version %s.'%(
                    migration_package.__name__, latest_version))
            new_mt = MigrationTracker(id=migration_package.__name__, version=latest_version)
            MigrationTracker.get_collection().insert(new_mt)
            continue
        if current_version > latest_version:
            raise DataError(_('The database for migration package %s is at version %s, which ' +\
                              'is larger than the latest version available, %s.')%(
                              migration_package.__name__, current_version, latest_version))
        if current_version == latest_version:
            print _('Migration package %s is up to date at version %s'%(migration_package.__name__,
                                                                        latest_version))
            continue
        # Filter out the unapplied migrations
        migrations = [migration for migration in migrations if migration.version > current_version]
        for migration in migrations:
            print _('Applying %s version %s'%(migration_package.__name__, migration.version))
            migration.migrate()
            MigrationTracker.get_collection().update({'id': migration_package.__name__},
                                                     {'$set': {'version': migration.version}},
                                                     safe=True)
            current_version = migration.version
            print _('Migration to %s version %s complete.'%(migration_package.__name__,
                                                            current_version))


def validate_database_migrations(options):
    errors = 0
    if not is_validated():
        errors = validate()
    if errors:
        error_message = _('%d errors on validation, see %s for details')%(errors, options.log_file)
        raise DataError(error_message)
    if not options.test:
        set_validated()


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
    if options.force:
        print _('Clearing previous versions.')
        clean_db()

    if options.start is not None:
        last = int(options.start) - 1
        print _('Reverting db to version %d.') % last
        revert_to_version(last)

    print _('Beginning database migrations.')
    migrate_database(options)
    print _('Database migrations complete.')

    print _('Loading content types.')
    load_content_types()
    print _('Content types loaded.')
    return os.EX_OK
