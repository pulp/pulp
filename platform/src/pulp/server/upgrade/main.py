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

from pulp.server.upgrade.db import (cds, consumers, events, repos, tasks, users)


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
    (repos.upgrade, _('Repositories, Content')),
)

# Default information about the database to upgrade
PULP_DATABASE_NAME = 'pulp_database'
DEFAULT_SEEDS = 'localhost:27017'

_LOG = logging.getLogger(__name__)


class UpgradeStepReport(object):
    """
    Captures the success/failure of an upgrade step and any messages to
    be displayed to the user. Any messages added to this report should be
    i18n'd before being passed in.
    """

    def __init__(self):
        self.success = None
        self.messages = []
        self.warnings = []
        self.errors = []

    def succeeded(self):
        self.success = True

    def failed(self):
        self.success = False

    def message(self, msg):
        self.messages.append(msg)

    def warning(self, msg):
        self.warnings.append(msg)

    def error(self, msg):
        self.errors.append(msg)


class InvalidStepReportException(Exception): pass


class StepException(Exception):

    def __init__(self, step_description):
        Exception.__init__(self, step_description)
        self.step_description = step_description

class Upgrader(object):
    """
    :ivar stream_file: full location to the file containing stream information;
          the file does not necessarily have to exist
    :type stream_file: str
    :ivar db_upgrade_calls: dictates which database upgrade steps will be performed;
          see DB_UPGRADE_CALLS comment above for a description of the entries
    :type db_upgrade_calls: list
    """

    def __init__(self,
                 stream_file=STREAM_FILE,
                 db_name=PULP_DATABASE_NAME,
                 db_seeds=DEFAULT_SEEDS,
                 db_upgrade_calls=DB_UPGRADE_CALLS):
        self.stream_file = stream_file

        self.db_name = db_name
        self.db_seeds = db_seeds
        self.db_upgrade_calls = db_upgrade_calls

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
            return

        self._upgrade_database()

    def _upgrade_database(self):
        self._print(_('Upgrading Database'))

        database = self._database(self.db_name, self.db_seeds)

        for db_call, description in self.db_upgrade_calls:
            self._print(_('Upgrading: %(d)s') % {'d' : description})
            spinner = ThreadedSpinner(self.prompt)
            spinner.start()

            try:
                report = db_call(database)
            except:
                spinner.stop()
                spinner.clear() # temporary until okaara supports this
                raise

            spinner.stop()
            spinner.clear() # temporary until okaara supports this

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

    # -- utilities ----------------------------------------------------------------

    def _print(self, line):
        _LOG.info(line)
        self.prompt.write(line)

    def _database(self, db_name, seeds):
        connection = Connection(seeds)
        database = getattr(connection, db_name)
        database.add_son_manipulator(NamespaceInjector())
        database.add_son_manipulator(AutoReference(database))
        return database

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
