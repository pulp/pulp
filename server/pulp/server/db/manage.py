"""
This module's main() function becomes the pulp-manage-db.py script.
"""
from datetime import datetime, timedelta
from gettext import gettext as _
from optparse import OptionParser
import logging
import os
import sys
import time
import traceback

from pulp.common import constants
from pulp.plugins.loader.api import load_content_types
from pulp.plugins.loader.manager import PluginManager
from pulp.server import logs
from pulp.server.db import connection
from pulp.server.db.migrate import models
from pulp.server.db import model
from pulp.server.db.migrations.lib import managers
from pulp.server.db.fields import UTCDateTimeField
from pulp.server.managers import factory, status
from pulp.server.managers.auth.role.cud import RoleManager, SUPER_USER_ROLE

from pymongo.errors import ServerSelectionTimeoutError

os.environ['DJANGO_SETTINGS_MODULE'] = 'pulp.server.webservices.settings'


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
    Create indexes before running any migration to avoid duplicates, e.g. in case a new collection
    is created.

    :param options: The command line parameters from the user
    """

    if not options.dry_run:
        ensure_database_indexes()

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
        elif migration_package.current_version == -1 and migration_package.allow_fast_forward:
            # -1 is the default for a brand-new tracker, so it indicates that no migrations
            # previously existed. Thus we can skip the migrations and fast-forward to the latest
            # version.
            log_args = {
                'v': migration_package.latest_available_version,
                'p': migration_package.name
            }
            if options.dry_run:
                unperformed_migrations = True
                _logger.info(_('Migration package %(p)s would have fast-forwarded '
                               'to version %(v)d' % log_args))
            else:
                # fast-forward if there is no pre-existing tracker
                migration_package._migration_tracker.version = \
                    migration_package.latest_available_version
                migration_package._migration_tracker.save()
                _logger.info(_('Migration package %(p)s fast-forwarded to '
                               'version %(v)d' % log_args))
            continue

        if migration_package.current_version == -1 and not migration_package.unapplied_migrations:
            # for a new migration package with no migrations, go ahead and track it at version 0
            log_args = {'n': migration_package.name}
            if options.dry_run:
                _logger.info(_('Would have tracked migration %(n)s at version 0') % log_args)
            else:
                _logger.info(_('Tracking migration %(n)s at version 0') % log_args)
                migration_package._migration_tracker.version = 0
                migration_package._migration_tracker.save()

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
                    message = _('Migration to %(p)s version %(v)s complete in %(t).3f seconds.')
                    message = message % {'p': migration_package.name,
                                         't': migration_package.duration,
                                         'v': migration_package.current_version}
                _logger.info(message)
        except models.MigrationRemovedError as e:
            # keep the log message simpler than the generic message below.
            _logger.critical(str(e))
            raise
        except Exception:
            # Log the error and what migration failed before allowing main() to handle the exception
            error_message = _('Applying migration %(m)s failed.\n\nHalting migrations due to a '
                              'migration failure.')
            error_message = error_message % {'m': migration.name}
            _logger.critical(error_message)
            raise

    if options.dry_run and unperformed_migrations:
        raise UnperformedMigrationException


def ensure_database_indexes():
    """
    Ensure that the minimal required indexes have been created for all collections.

    Gratuitously create MongoEngine based models indexes if they do not already exist.
    """

    model.Importer.ensure_indexes()
    model.RepositoryContentUnit.ensure_indexes()
    model.Repository.ensure_indexes()
    model.ReservedResource.ensure_indexes()
    model.TaskStatus.ensure_indexes()
    model.Worker.ensure_indexes()
    model.CeleryBeatLock.ensure_indexes()
    model.ResourceManagerLock.ensure_indexes()
    model.LazyCatalogEntry.ensure_indexes()
    model.DeferredDownload.ensure_indexes()
    model.Distributor.ensure_indexes()

    # Load all the model classes that the server knows about and ensure their indexes as well
    plugin_manager = PluginManager()
    for unit_type, model_class in plugin_manager.unit_models.items():
        unit_key_index = {'fields': model_class.unit_key_fields, 'unique': True}
        for index in model_class._meta['indexes']:
            if isinstance(index, dict) and 'fields' in index:
                if list(index['fields']) == list(unit_key_index['fields']):
                    raise ValueError("Content unit type '%s' explicitly defines an index for its "
                                     "unit key. This is not allowed because the platform handles"
                                     "it for you." % unit_type)
        model_class._meta['indexes'].append(unit_key_index)
        model_class._meta['index_specs'] = \
            model_class._build_index_specs(model_class._meta['indexes'])
        model_class.ensure_indexes()

    for model_type, model_class in plugin_manager.auxiliary_models.items():
        model_class._meta['index_specs'] = \
            model_class._build_index_specs(model_class._meta['indexes'])
        model_class.ensure_indexes()


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
        active_workers = None

        if not options.dry_run:
            active_workers = status.get_workers()

        if active_workers:
            last_worker_time = max([worker['last_heartbeat'] for worker in active_workers])
            time_from_last = UTCDateTimeField().to_python(datetime.utcnow()) - last_worker_time
            wait_time = timedelta(seconds=constants.MIGRATION_WAIT_TIME) - time_from_last

            if wait_time > timedelta(0):
                print _('\nThe following processes might still be running:')
                for worker in active_workers:
                    print _('\t%s' % worker['name'])

                for i in range(wait_time.seconds, 0, -1):
                    print _('\rPlease wait %s seconds while Pulp confirms this.' % i),
                    sys.stdout.flush()
                    time.sleep(1)

                still_active_workers = [worker for worker in status.get_workers() if
                                        worker['last_heartbeat'] > last_worker_time]

                if still_active_workers:
                    print >> sys.stderr, _('\n\nThe following processes are still running, please'
                                           ' stop the running workers before retrying the'
                                           ' pulp-manage-db command.')
                    for worker in still_active_workers:
                        print _('\t%s' % worker['name'])

                    return os.EX_SOFTWARE
        return _auto_manage_db(options)
    except UnperformedMigrationException:
        return 1
    except DataError, e:
        _logger.critical(str(e))
        _logger.critical(''.join(traceback.format_exception(*sys.exc_info())))
        return os.EX_DATAERR
    except models.MigrationRemovedError:
        return os.EX_SOFTWARE
    except ServerSelectionTimeoutError:
        _logger.info(_('Cannot connect to the database, please validate that the database is online'
                       ' and accessible.'))
        return os.EX_SOFTWARE
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

    message = _('Loading content types.')
    _logger.info(message)
    # Note that if dry_run is False, None is always returned
    old_content_types = load_content_types(dry_run=options.dry_run)
    if old_content_types:
        for content_type in old_content_types:
            message = _(
                'Would have created or updated the following type definition: ' + content_type.id)
            _logger.info(message)
    message = _('Content types loaded.')
    _logger.info(message)

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

    user_manager = managers.UserManager()
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
    # Django will un-set our default ignoring DeprecationWarning *unless* sys.warnoptions is set.
    # So, set it as though '-W ignore::DeprecationWarning' was passed on the commandline. Our code
    # that sets DeprecationWarnings as ignored also checks warnoptions, so this must be added after
    # pulp.server.logs.start_logging is called but before Django is initialized.
    sys.warnoptions.append('ignore::DeprecationWarning')
