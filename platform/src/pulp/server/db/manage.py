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

from gettext import gettext as _
from optparse import OptionParser
import logging
import traceback
import os
import sys

from pulp.plugins.loader.api import load_content_types
from pulp.server.db import connection
from pulp.server.db.migrate import models
from pulp.server import config, logs


connection.initialize()
logger = None


class DataError(Exception):
    """
    This Exception is used when we want to return the os.EX_DATAERR code.
    """
    pass


def parse_args():
    """
    Parse the command line arguments into the flags that we accept. Returns the parsed options.
    """
    parser = OptionParser()
    parser.add_option('--test', action='store_true', dest='test',
                      default=False,
                      help=_('Run migration, but do not update version'))
    options, args = parser.parse_args()
    if args:
        parser.error(_('Unknown arguments: %s') % ', '.join(args))
    return options


def migrate_database(options):
    """
    Perform the migrations for each migration package found in pulp.server.db.migrations.

    :param options: The command line parameters from the user
    """
    migration_packages = models.get_migration_packages()
    for migration_package in migration_packages:
        if migration_package.current_version > migration_package.latest_available_version:
            raise DataError(_('The database for migration package %(p)s is at version %(v)s, ' +\
                              'which is larger than the latest version available, %(a)s.')%({
                                'p': migration_package.name, 'v': migration_package.current_version,
                                'a': migration_package.latest_available_version}))
        if migration_package.current_version == migration_package.latest_available_version:
            message = _('Migration package %(p)s is up to date at version %(v)s'%({
                'p': migration_package.name,
                'v': migration_package.latest_available_version}))
            logger.info(message)
            print message
            continue

        try:
            for migration in migration_package.unapplied_migrations:
                message = _('Applying %(p)s version %(v)s'%({
                    'p': migration_package.name, 'v': migration.version}))
                print message
                logger.info(message)
                # We pass in !options.test to stop the apply_migration method from updating the
                # package's current version when the --test flag is set
                migration_package.apply_migration(migration,
                                                  update_current_version=not options.test)
                message = _('Migration to %(p)s version %(v)s complete.'%(
                    {'p': migration_package.name, 'v': migration_package.current_version}))
                print message
                logger.info(message)
        except Exception, e:
            # If an Exception is raised while applying the migrations, we should log and print it,
            # and then continue with the other packages.
            error_message = _('Applying migration %(m)s failed.')%(
                              {'m': migration.name})
            print >> sys.stderr, str(error_message), _(' See log for details.')
            logger.critical(error_message)
            logger.critical(str(e))
            logger.critical(''.join(traceback.format_exception(*sys.exc_info())))


def main():
    """
    This is the high level entry method. It does logging if any Exceptions are raised.
    """
    try:
        options = parse_args()
        _start_logging()
        _auto_manage_db(options)
    except DataError, e:
        print >> sys.stderr, str(e)
        logger.critical(str(e))
        logger.critical(''.join(traceback.format_exception(*sys.exc_info())))
        return os.EX_DATAERR
    except Exception, e:
        print >> sys.stderr, str(e)
        logger.critical(str(e))
        logger.critical(''.join(traceback.format_exception(*sys.exc_info())))
        return os.EX_SOFTWARE


def _auto_manage_db(options):
    """
    Find and apply all available database migrations, and install or update all available content
    types.

    :param options: The command line parameters from the user.
    """
    message = _('Beginning database migrations.')
    print message
    logger.info(message)
    migrate_database(options)
    message = _('Database migrations complete.')
    print message
    logger.info(message)

    message = _('Loading content types.')
    print message
    logger.info(message)
    load_content_types()
    message = _('Content types loaded.')
    print message
    logger.info(message)
    return os.EX_OK


def _start_logging():
    """
    Call into Pulp to get the logging started, and set up the logger to be used in this module.
    """
    global logger
    log_config_filename = config.config.get('logs', 'db_config')
    if not os.access(log_config_filename, os.R_OK):
        raise RuntimeError("Unable to read log configuration file: %s" % (log_config_filename))
    logging.config.fileConfig(log_config_filename)
    logger = logging.getLogger('db')
