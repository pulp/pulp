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
import sys

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

# -- classes ------------------------------------------------------------------

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
        Exception.__init__(step_description)
        self.step_description = step_description

# -- upgrade operations -------------------------------------------------------

def upgrade(stream_file=STREAM_FILE,
            db_name=PULP_DATABASE_NAME,
            db_seeds=DEFAULT_SEEDS,
            db_upgrade_calls=DB_UPGRADE_CALLS):
    """
    Performs the upgrade process if the installation qualifies to be upgraded.

    :param stream_file: full location to the file containing stream information;
           the file does not necessarily have to exist
    :type  stream_file: str
    :param db_upgrade_calls: dictates which database upgrade steps will be performed;
           see DB_UPGRADE_CALLS comment above for a description of the entries
    :type  db_upgrade_calls: list

    :return: nothing if the upgrade was successful

    :raise InvalidStepReportException: if any of the steps does not properly
           indicate its success or failure; should only occur during development
    :raise StepException: if a step raises an error or indicates it failed
    """

    prompt = Prompt(output=_UberWriter())

    if not _is_v1(stream_file):
        prompt.write(_('Pulp installation is already upgraded to the latest version'))
        return

    _upgrade_database(prompt, db_name, db_seeds, db_upgrade_calls)


def _upgrade_database(prompt, name, seeds, upgrade_calls):
    prompt.write(_('Upgrading Database'))

    database = _database(name, seeds)

    for db_call, description in upgrade_calls:
        prompt.write(_('Upgrading: %(d)') % description)
        spinner = ThreadedSpinner(prompt)
        spinner.start()

        report = UpgradeStepReport()
        try:
            db_call(database, report)
        except:
            spinner.stop()
            raise

        spinner.stop()

        if report.success is None:
            # This should only happen during development if the script writer
            # didn't properly configure the report and must be fixed before
            # release
            prompt.write(_('Database upgrade script did not indicate the result of the step'))
            raise InvalidStepReportException()

        if report.success:
            _print_report_data(prompt, _('Messages'), report.messages)
            _print_report_data(prompt, _('Warnings'), report.warnings)
        else:
            _print_report_data(prompt, _('Warnings'), report.warnings)
            _print_report_data(prompt, _('Errors'), report.errors)
            raise StepException(description)

        prompt.write('')

# -- utilities ----------------------------------------------------------------

def _database(db_name, seeds):
    connection = Connection(seeds)
    database = getattr(connection, db_name)
    database.add_son_manipulator(NamespaceInjector())
    database.add_son_manipulator(AutoReference(_database))
    return database


def _print_report_data(prompt, title, items):
    if len(items) > 0:
        prompt.write(title)
        for i in items:
            prompt.write('  %s' % i)


def _is_v1(stream_file):
    """
    Returns whether or not the current installation is a v1 stream build.

    :return: True if the installation is a v1 build, False otherwise
    :rtype:  bool
    """

    # Eventually this will check the contents of that file, but for now the
    # quickest solution is just to check its existence

    return not os.path.exists(stream_file)


class _UberWriter(object):
    """
    Writer implementation to pass to an okaara prompt to log to both a log
    and standard output.
    """

    def write(self, line):
        sys.stdout.write(line)
        _LOG.info(line)

