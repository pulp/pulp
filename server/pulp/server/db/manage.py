"""
This module's main() function becomes the pulp-manage-db.py script.
"""
from gettext import gettext as _
from optparse import OptionParser
import logging
import os
import sys
import traceback

from pulp.server import logs
from pulp.server.db import connection
from pulp.server.db.migrate import models
from pulp.server.managers import factory
from pulp.server.managers.auth.role.cud import RoleManager, SUPER_USER_ROLE
from pulp.server.managers.auth.user.cud import UserManager


_logger = None


class DataError(Exception):
    """
    This Exception is used when we want to return the os.EX_DATAERR code.
    """
    pass


class UnperformedMigrationException(Exception):
    """
    This exception is raised when there are unperformed exceptions.
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
    parser.add_option('--dry-run', action='store_true', dest='dry_run', default=False,
                      help=_('Perform a dry run with no changes made. Returns 1 if there are '
                             'migrations to apply.'))
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
    unperformed_migrations = False
    for migration_package in migration_packages:
        if migration_package.current_version > migration_package.latest_available_version:
            msg = _('The database for migration package %(p)s is at version %(v)s, which is larger '
                    'than the latest version available, %(a)s.')
            msg = msg % ({'p': migration_package.name, 'v': migration_package.current_version,
                          'a': migration_package.latest_available_version})
            raise DataError(msg)
        if migration_package.current_version == migration_package.latest_available_version:
            message = _('Migration package %(p)s is up to date at version %(v)s')
            message = message % {'p': migration_package.name,
                                 'v': migration_package.latest_available_version}
            _logger.info(message)
            continue

        try:
            for migration in migration_package.unapplied_migrations:
                message = _('Applying %(p)s version %(v)s')
                message = message % {'p': migration_package.name, 'v': migration.version}
                _logger.info(message)
                if options.dry_run:
                    unperformed_migrations = True
                    message = _('Would have applied migration to %(p)s version %(v)s')
                    message = message % {'p': migration_package.name, 'v': migration.version}
                else:
                    # We pass in !options.test to stop the apply_migration method from updating the
                    # package's current version when the --test flag is set
                    migration_package.apply_migration(migration,
                                                      update_current_version=not options.test)
                    message = _('Migration to %(p)s version %(v)s complete.')
                    message = message % {'p': migration_package.name,
                                         'v': migration_package.current_version}
                _logger.info(message)
        except Exception:
            # Log the error and what migration failed before allowing main() to handle the exception
            error_message = _('Applying migration %(m)s failed.\n\nHalting migrations due to a '
                              'migration failure.')
            error_message = error_message % {'m': migration.name}
            _logger.critical(error_message)
            raise

    if options.dry_run and unperformed_migrations:
        raise UnperformedMigrationException


def main():
    """
    This is the high level entry method. It does logging if any Exceptions are raised.
    """
    if os.getuid() == 0:
        print >> sys.stderr, _('This must not be run as root, but as the same user apache runs as.')
        return os.EX_USAGE
    try:
        options = parse_args()
        _start_logging()
        connection.initialize(max_timeout=1)
        return _auto_manage_db(options)
    except UnperformedMigrationException:
        return 1
    except DataError, e:
        _logger.critical(str(e))
        _logger.critical(''.join(traceback.format_exception(*sys.exc_info())))
        return os.EX_DATAERR
    except Exception, e:
        _logger.critical(str(e))
        _logger.critical(''.join(traceback.format_exception(*sys.exc_info())))
        return os.EX_SOFTWARE


def _auto_manage_db(options):
    """
    Find and apply all available database migrations, and install or update all available content
    types.

    :param options: The command line parameters from the user.
    """
    unperformed_migrations = False

    message = _('Ensuring the admin role and user are in place.')
    _logger.info(message)
    # Due to the silliness of the factory, we have to initialize it because the UserManager and
    # RoleManager are going to try to use it.
    factory.initialize()
    role_manager = RoleManager()
    if options.dry_run:
        if not role_manager.get_role(SUPER_USER_ROLE):
            unperformed_migrations = True
            message = _('Would have created the admin role.')
            _logger.info(message)
    else:
        role_manager.ensure_super_user_role()

    user_manager = UserManager()
    if options.dry_run:
        if not user_manager.get_admins():
            unperformed_migrations = True
            message = _('Would have created the default admin user.')
            _logger.info(message)
    else:
        user_manager.ensure_admin()
    message = _('Admin role and user are in place.')
    _logger.info(message)

    message = _('Beginning database migrations.')
    _logger.info(message)
    migrate_database(options)
    message = _('Database migrations complete.')
    _logger.info(message)

    if unperformed_migrations:
        return 1

    return os.EX_OK


def _start_logging():
    """
    Call into Pulp to get the logging started, and set up the _logger to be used in this module.
    """
    global _logger
    logs.start_logging()
    _logger = logging.getLogger(__name__)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    _logger.root.addHandler(console_handler)
