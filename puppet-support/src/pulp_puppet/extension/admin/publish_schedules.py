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

from gettext import gettext as _

from pulp.client.commands.schedule import (\
    DeleteScheduleCommand, ListScheduleCommand, CreateScheduleCommand,
    UpdateScheduleCommand, NextRunCommand, ScheduleStrategy)
from pulp.client.commands.options import OPTION_REPO_ID

from pulp_puppet.common.constants import DISTRIBUTOR_ID

# -- constants ----------------------------------------------------------------

DESC_LIST = _('list scheduled publish operations')
DESC_CREATE = _('adds a new scheduled publish operation')
DESC_DELETE = _('delete a publish schedule')
DESC_UPDATE = _('updates an existing schedule')
DESC_NEXT_RUN = _('displays the next scheduled publish run for a repository')

# -- commands -----------------------------------------------------------------

class PuppetListScheduleCommand(ListScheduleCommand):
    def __init__(self, context):
        strategy = RepoPublishSchedulingStrategy(context)
        super(PuppetListScheduleCommand, self).__init__(context, strategy,
                                                        description=DESC_LIST)
        self.add_option(OPTION_REPO_ID)


class PuppetCreateScheduleCommand(CreateScheduleCommand):
    def __init__(self, context):
        strategy = RepoPublishSchedulingStrategy(context)
        super(PuppetCreateScheduleCommand, self).__init__(context, strategy,
                                                          description=DESC_CREATE)
        self.add_option(OPTION_REPO_ID)


class PuppetDeleteScheduleCommand(DeleteScheduleCommand):
    def __init__(self, context):
        strategy = RepoPublishSchedulingStrategy(context)
        super(PuppetDeleteScheduleCommand, self).__init__(context, strategy,
                                                          description=DESC_DELETE)
        self.add_option(OPTION_REPO_ID)


class PuppetUpdateScheduleCommand(UpdateScheduleCommand):
    def __init__(self, context):
        strategy = RepoPublishSchedulingStrategy(context)
        super(PuppetUpdateScheduleCommand, self).__init__(context, strategy,
                                                          description=DESC_UPDATE)
        self.add_option(OPTION_REPO_ID)


class PuppetNextRunCommand(NextRunCommand):
    def __init__(self, context):
        strategy = RepoPublishSchedulingStrategy(context)
        super(PuppetNextRunCommand, self).__init__(context, strategy,
                                                   description=DESC_NEXT_RUN)
        self.add_option(OPTION_REPO_ID)

# -- internal -----------------------------------------------------------------

class RepoPublishSchedulingStrategy(ScheduleStrategy):

    # See super class for method documentation

    def __init__(self, context):
        super(RepoPublishSchedulingStrategy, self).__init__()
        self.context = context
        self.api = context.server.repo_publish_schedules

    def create_schedule(self, schedule, failure_threshold, enabled, kwargs):
        repo_id = kwargs[OPTION_REPO_ID.keyword]

        # Eventually we'll support passing in publish arguments to the scheduled
        # call. When we do, override_config will be created here from kwargs.
        override_config = {}

        return self.api.add_schedule(repo_id, DISTRIBUTOR_ID, schedule,
                                     override_config, failure_threshold, enabled)

    def delete_schedule(self, schedule_id, kwargs):
        repo_id = kwargs[OPTION_REPO_ID.keyword]
        return self.api.delete_schedule(repo_id, DISTRIBUTOR_ID, schedule_id)

    def retrieve_schedules(self, kwargs):
        repo_id = kwargs[OPTION_REPO_ID.keyword]
        return self.api.list_schedules(repo_id, DISTRIBUTOR_ID)

    def update_schedule(self, schedule_id, **kwargs):
        repo_id = kwargs.pop(OPTION_REPO_ID.keyword)
        return self.api.update_schedule(repo_id, DISTRIBUTOR_ID, schedule_id, **kwargs)
