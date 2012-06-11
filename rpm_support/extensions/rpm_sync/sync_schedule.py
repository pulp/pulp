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

from rpm_sync.schedule import (DeleteScheduleCommand, ListScheduleCommand, CreateScheduleCommand,
                      UpdateScheduleCommand, NextRunCommand, ScheduleStrategy)

from pulp.client.extensions.extensions import PulpCliSection, PulpCliOption

# -- constants ----------------------------------------------------------------

YUM_IMPORTER_ID = 'yum_importer' # same as used in repo create

REPO_ID_ARG = 'repo-id'

# -- framework classes --------------------------------------------------------

class RepoSyncSchedulingSection(PulpCliSection):

    def __init__(self, context, name, description):
        PulpCliSection.__init__(self, name, description)

        strategy = RepoSyncSchedulingStrategy(context)

        repo_id_option = PulpCliOption('--%s' % REPO_ID_ARG, _('identifies the repository'), required=True)

        list_command = ListScheduleCommand(context, strategy, 'list', _('list scheduled sync operations'))
        list_command.add_option(repo_id_option)

        create_command = CreateScheduleCommand(context, strategy, 'create', _('adds a new scheduled sync operation'))
        create_command.add_option(repo_id_option)

        delete_command = DeleteScheduleCommand(context, strategy, 'delete', _('delete a sync schedule'))
        delete_command.add_option(repo_id_option)

        update_command = UpdateScheduleCommand(context, strategy, 'update', _('updates an existing schedule'))
        update_command.add_option(repo_id_option)

        next_run_command = NextRunCommand(context, strategy, 'next', _('displays the next scheduled sync run for a repository'))
        next_run_command.add_option(repo_id_option)

        self.add_command(list_command)
        self.add_command(create_command)
        self.add_command(delete_command)
        self.add_command(update_command)
        self.add_command(next_run_command)

class RepoSyncSchedulingStrategy(ScheduleStrategy):

    # See super class for method documentation

    def __init__(self, context):
        super(RepoSyncSchedulingStrategy, self).__init__()
        self.context = context
        self.api = context.server.repo_sync_schedules

    def create_schedule(self, schedule, failure_threshold, enabled, kwargs):
        repo_id = kwargs[REPO_ID_ARG]

        # Eventually we'll support passing in sync arguments to the scheduled
        # call. When we do, override_config will be created here from kwargs.
        override_config = {}

        return self.api.add_schedule(repo_id, YUM_IMPORTER_ID, schedule, override_config, failure_threshold, enabled)

    def delete_schedule(self, schedule_id, kwargs):
        repo_id = kwargs[REPO_ID_ARG]
        return self.api.delete_schedule(repo_id, YUM_IMPORTER_ID, schedule_id)

    def retrieve_schedules(self, kwargs):
        repo_id = kwargs[REPO_ID_ARG]
        return self.api.list_schedules(repo_id, YUM_IMPORTER_ID)

    def update_schedule(self, schedule_id, **kwargs):
        repo_id = kwargs.pop(REPO_ID_ARG)
        return self.api.update_schedule(repo_id, YUM_IMPORTER_ID, schedule_id, **kwargs)
