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

from rpm_sync.publish_schedule import RepoPublishSchedulingSection
from rpm_sync import sync as sync_commands
from rpm_sync import publish as publish_commands
from rpm_sync.sync_schedule import RepoSyncSchedulingSection

# -- framework hook -----------------------------------------------------------

def initialize(context):

    global LOG
    LOG = context.logger

    # Override the repo sync command
    repo_section = context.cli.find_section('repo')
    repo_section.remove_subsection('sync')
    repo_section.remove_subsection('publish')

    # Sync Commands
    sync_section = repo_section.create_subsection('sync', _('run, schedule, or view the status of sync tasks'))
    sync_section.add_command(sync_commands.RunSyncCommand(context, 'run', _('triggers an immediate sync of a repository')))
    sync_section.add_command(sync_commands.StatusCommand(context, 'status', _('displays the status of a repository\'s sync tasks')))

    sync_schedule_subsection = RepoSyncSchedulingSection(context, 'schedules', _('manage sync schedules for a repository'))
    sync_section.add_subsection(sync_schedule_subsection)


    # Publish Commands
    publish_section = repo_section.create_subsection('publish', _('run, schedule, or view the status of publish tasks'))
    publish_section.add_command(publish_commands.RunPublishCommand(context, 'run', _('triggers an immediate publish of a repository')))
    publish_section.add_command(publish_commands.StatusCommand(context, 'status', _('displays the status of a repository\'s publish tasks')))

    publish_schedule_subsection = RepoPublishSchedulingSection(context, 'schedules', _('manage puslish schedules for a repository'))
    publish_section.add_subsection(publish_schedule_subsection)

