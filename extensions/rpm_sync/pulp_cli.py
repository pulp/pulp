# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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

from sync import RunSyncCommand, StatusCommand
from sync_schedule import RepoSyncSchedulingSection

# -- framework hook -----------------------------------------------------------

def initialize(context):

    if not context.extension_config.getboolean('main', 'enabled'):
        return

    global LOG
    LOG = context.logger

    # Override the repo sync command
    repo_section = context.cli.find_section('repo')
    sync_section = repo_section.find_subsection('sync')

    # Sync Commands
    sync_section.remove_command('run')
    sync_section.add_command(RunSyncCommand(context, 'run', _('triggers an immediate sync of a repository')))
    sync_section.add_command(StatusCommand(context, 'status', _('displays the status of a repository\'s sync operations')))

    # Schedule Commands
    sync_schedule_subsection = RepoSyncSchedulingSection(context, 'schedules', _('manage sync schedules for a repository'))
    sync_section.add_subsection(sync_schedule_subsection)
