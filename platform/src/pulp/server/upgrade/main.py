# -*- coding: utf-8 -*-
# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Methods that drive the entire v1 to v2 upgrade process.
"""

from gettext import gettext as _
import logging
import os

from okaara.prompt import Prompt
from okaara.progress import ThreadedSpinner
from pymongo import Connection
from pymongo.son_manipulator import AutoReference, NamespaceInjector

from pulp.server.upgrade.db import (all_repos, cds, consumers, events, iso_repos,
                                    migrations, tasks, unit_count, units, users,
                                    yum_repos)
from pulp.server.upgrade.filesystem import (clean, distribution, isos,
                                            permissions, repos, rpms)


# Indicates which Pulp stream (v1, v2, etc.) is installed
STREAM_FILE = '/var/lib/pulp/stream'

# These will be executed sequentially so be careful when changing the order
# Each entry is a tuple of: method to execite, step description
DB_UPGRADE_CALLS = (
    (cds.upgrade, _('CDS')),
    (consumers.upgrade, _('Consumers')),
    (events.upgrade, _('Event')),
    (users.upgrade, _('Users, Permissions, and Roles')),
    (tasks.upgrade, _('Tasks')),
    (yum_repos.upgrade, _('Repositories, Content')),
    (iso_repos.upgrade, _('File Repositories, Content')),
    (all_repos.upgrade, _('Repository Groups, Sync Schedules')),
    (units.upgrade, _('Packages, Errata, and Distributions')),
    (unit_count.upgrade, _('Calculate Repository Content Counts')),
    (migrations.upgrade, _('Database Migration Initialization')),
)

FILES_UPGRADE_CALLS = (
    (rpms.upgrade, _('RPMs, SRPMs, DRPMs')),
    (distribution.upgrade, _('Distributions')),
    (isos.upgrade, _('ISOs')),
    (repos.upgrade, _('Repository Working Directories')),
    (permissions.upgrade, _('Filesystem Permissions')), # has to be after all content upgrades
)

# Separating so we can easily disable it during testing
CLEAN_UPGRADE_CALLS = (
    (clean.upgrade, _('v1 Directories')),
)

    # Name of the production Pulp database
PULP_DATABASE_NAME = 'pulp_database'

# Name of the temporary database used to assemble the v2 database
TEMP_DATABASE_NAME = 'pulp_v2_tmp'

# Name the v1 database will be backed up to if configured to do so
V1_BACKUP_DATABASE_NAME = 'pulp_database_v1'

# If not explicitly specified, used for connecting to mongo
DEFAULT_SEEDS = 'localhost:27017'

_LOG = logging.getLogger(__name__)


class InvalidStepReportException(Exception):
    """
    Indicates a step didn't return the proper status. Should only occur during
    development.
    """
    pass


class StepException(Exception):
    """
    Describes why a step failed.
    """

    def __init__(self, step_description):
        Exception.__init__(self, step_description)
        self.step_description = step_description


class Upgrader(object):
    """
    :ivar stream_file: full location to the file containing stream information;
          the file does not necessarily have to exist
    :type stream_file: str

    :ivar upgrade_db: configures whether or not the DB upgrade scripts will be run;
          if this is False, the clean step will be skipped regardless of
          its configured value
    :type upgrade_db: bool

    :ivar db_upgrade_calls: dictates which database upgrade steps will be performed;
          see DB_UPGRADE_CALLS comment above for a description of the entries.
    :type db_upgrade_calls: list

    :ivar db_seeds: seeds for accessing MongoDB
    :type db_seeds: str

    :ivar upgrade_files: configures whether or not the filesystem upgrade scripts
                         will be run; if this is False, the clean step will be
                         skipped regardless of its configured value
    :type upgrade_files: bool

    :ivar files_upgrade_calls: dictates which filesystem upgrade steps will be
          performed; see FILES_UPGRADE_CALLS for a description of the entries
    :type files_upgrade_calls: list

    :ivar install_db: dictates if the temporary database created by the build
          DB step will replace the production database and delete the temp
    :type install_db: bool

    :ivar clean: dictates if the filesystem clean up operations will be run
    :type clean: bool
    """

    def __init__(self,
                 stream_file=STREAM_FILE,
                 prod_db_name=PULP_DATABASE_NAME,
                 tmp_db_name=TEMP_DATABASE_NAME,
                 v1_backup_db_name=V1_BACKUP_DATABASE_NAME,
                 backup_v1_db=False,
                 upgrade_db=True,
                 db_seeds=DEFAULT_SEEDS,
                 db_upgrade_calls=DB_UPGRADE_CALLS,
                 upgrade_files=True,
                 files_upgrade_calls=FILES_UPGRADE_CALLS,
                 install_db=True,
                 clean=True):
        self.stream_file = stream_file

        self.prod_db_name = prod_db_name
        self.tmp_db_name = tmp_db_name
        self.v1_backup_db_name = v1_backup_db_name

        self.backup_v1_db = backup_v1_db

        self.upgrade_db = upgrade_db
        self.db_seeds = db_seeds
        self.db_upgrade_calls = db_upgrade_calls

        self.upgrade_files = upgrade_files
        self.files_upgrade_calls = files_upgrade_calls

        self.install_db = install_db
        self.clean = clean

        self.prompt = Prompt()

    def upgrade(self):
        """
        Performs the upgrade process if the installation qualifies to be upgraded.

        :return: nothing if the upgrade was successful

        :raise InvalidStepReportException: if any of the steps does not properly
               indicate its success or failure; should only occur during development
        :raise StepException: if a step raises an error or indicates it failed
        """

        if not self._is_v1():
            self._print(_('Pulp installation is already upgraded to the latest version'))
            self._print('')
            return

        if not self.upgrade_db:
            self._print(_('Skipping Database Upgrade'))
            self._print('')
        else:
            self._upgrade_database()

        if not self.upgrade_files:
            self._print(_('Skipping Filesystem Upgrade'))
            self._print('')
        else:
            self._upgrade_files()

        if not self.install_db:
            self._print(_('Skipping v2 Database Installation'))
            self._print('')
        else:
            self._install()

        # The files are used in both the upgrade DB and upgrade files step, so
        # if either are skipped, assume they'll be run again in the future
        # and automatically skip the clean
        if not self.clean or not self.upgrade_files or not self.upgrade_db:
            self._print(_('Skipping v1 Filesystem Clean Up'))
            self._print('')
        else:
            self._clean()

        self._drop_stream_flag()

    def _upgrade_database(self):
        """
        Runs all configured upgrade scripts for handling the database.
        """

        self._print(_('= Upgrading Database ='))

        v1_database = self._database(self.prod_db_name)
        tmp_database = self._database(self.tmp_db_name)

        for db_call, description in self.db_upgrade_calls:
            self._print(_('Upgrading: %(d)s') % {'d' : description})
            spinner = ThreadedSpinner(self.prompt)
            spinner.start()

            try:
                report = db_call(v1_database, tmp_database)
            except:
                spinner.stop(clear=True)
                raise

            spinner.stop(clear=True)

            if report is None or report.success is None:
                # This should only happen during development if the script writer
                # didn't properly configure the report and must be fixed before
                # release
                self._print(_('Database upgrade script did not indicate the result of the step'))
                raise InvalidStepReportException()

            if report.success:
                self._print_report_data(_('Messages'), report.messages)
                self._print_report_data(_('Warnings'), report.warnings)
            else:
                self._print_report_data(_('Warnings'), report.warnings)
                self._print_report_data(_('Errors'), report.errors)
                raise StepException(description)

            self.prompt.write('')

    def _upgrade_files(self):
        """
        Runs all configured upgrade scripts for handling the filesystem.
        """

        self._print(_('= Upgrading Pulp Files ='))

        v1_database = self._database(self.prod_db_name)
        tmp_database = self._database(self.tmp_db_name)

        for upgrade_call, description in self.files_upgrade_calls:
            self._print(_('Upgrading: %(d)s') % {'d' : description})
            spinner = ThreadedSpinner(self.prompt)
            spinner.start()

            try:
                report = upgrade_call(v1_database, tmp_database)
            except:
                spinner.stop(clear=True)
                raise

            spinner.stop(clear=True)

            if report is None or report.success is None:
                # This should only happen during development if the script writer
                # didn't properly configure the report and must be fixed before
                # release
                self._print(_('Filesystem upgrade script did not indicate the result of the step'))
                raise InvalidStepReportException()

            if report.success:
                self._print_report_data(_('Messages'), report.messages)
                self._print_report_data(_('Warnings'), report.warnings)
            else:
                self._print_report_data(_('Warnings'), report.warnings)
                self._print_report_data(_('Errors'), report.errors)
                raise StepException(description)

            self.prompt.write('')

    def _install(self):

        # Backup
        if self.backup_v1_db:
            self._print(_('Backing up the v1 database to %(db)s') % {'db' : self.v1_backup_db_name})

            spinner = ThreadedSpinner(self.prompt)
            spinner.start()
            self._backup_v1()
            spinner.stop(clear=True)
        else:
            self._print(_('The v1 database will not be backed up'))
            self.prompt.write('')

        # Install
        self._print(_('Installing the v2 Database'))

        spinner = ThreadedSpinner(self.prompt)
        spinner.start()
        self._install_v2()
        spinner.stop(clear=True)

        self.prompt.write('')

        # Clean Up
        self._print(_('Deleting v2 Temporary Database'))

        spinner = ThreadedSpinner(self.prompt)
        spinner.start()
        self._cleanup()
        spinner.stop(clear=True)

        self.prompt.write('')

    def _clean(self):

        self._print(_('= Clean Up ='))

        v1_database = self._database(self.prod_db_name)
        tmp_database = self._database(self.tmp_db_name)

        for upgrade_call, description in CLEAN_UPGRADE_CALLS:
            self._print(_('Cleaning: %(d)s') % {'d' : description})
            spinner = ThreadedSpinner(self.prompt)
            spinner.start()

            try:
                report = upgrade_call(v1_database, tmp_database)
            except:
                spinner.stop(clear=True)
                raise

            spinner.stop(clear=True)

            if report is None or report.success is None:
                self._print(_('Clean upgrade script did not indicate the result of the step'))
                raise InvalidStepReportException()

            if report.success:
                self._print_report_data(_('Messages'), report.messages)
                self._print_report_data(_('Warnings'), report.warnings)
            else:
                self._print_report_data(_('Warnings'), report.warnings)
                self._print_report_data(_('Errors'), report.errors)
                raise StepException(description)

            self.prompt.write('')

    def _drop_stream_flag(self):
        """
        Creates the stream flag that is used to prevent multiple runs of the
        upgrade
        """
        f = open(self.stream_file, 'w')
        f.write('v2')
        f.close()

    # -- utilities ----------------------------------------------------------------

    def _connection(self):
        connection = Connection(self.db_seeds)
        return connection

    def _database(self, db_name):
        connection = self._connection()
        database = getattr(connection, db_name)
        database.add_son_manipulator(NamespaceInjector())
        database.add_son_manipulator(AutoReference(database))
        return database

    def _backup_v1(self):
        connection = self._connection()
        connection.copy_database(self.prod_db_name, self.v1_backup_db_name)

    def _install_v2(self):
        connection = self._connection()
        connection.drop_database(self.prod_db_name)
        connection.copy_database(self.tmp_db_name, self.prod_db_name)

    def _cleanup(self):
        connection = self._connection()
        connection.drop_database(self.tmp_db_name)

    def _print(self, line):
        _LOG.info(line)
        self.prompt.write(line)

    def _print_report_data(self, title, items):
        if len(items) > 0:
            self._print(title)
            for i in items:
                self._print('  %s' % i)

    def _is_v1(self):
        """
        Returns whether or not the current installation is a v1 stream build.

        :return: True if the installation is a v1 build, False otherwise
        :rtype:  bool
        """

        # Eventually this will check the contents of that file, but for now the
        # quickest solution is just to check its existence

        result = not os.path.exists(self.stream_file)
        return result
