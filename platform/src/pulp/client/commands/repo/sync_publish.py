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

"""
Commands and hooks for creating and using sync, publish, and progress status
commands.
"""

from gettext import gettext as _

from pulp.client.commands import options
from pulp.client.commands.repo.status import status, tasks
from pulp.client.extensions.extensions import PulpCliCommand

# -- constants ----------------------------------------------------------------

# Command Descriptions

DESC_SYNC_RUN = _('triggers an immediate sync of a repository')
DESC_STATUS = _('displays the status of a repository\'s sync tasks')

NAME_BACKGROUND = 'bg'
DESC_BACKGROUND = _('if specified, the CLI process will end but the sync will continue on '
                    'the server; the progress can be later displayed using the status command')

# -- hooks --------------------------------------------------------------------

class StatusRenderer(object):

    def __init__(self, context):
        self.context = context
        self.prompt = context.prompt

    def display_report(self, progress_report):
        raise NotImplementedError()

# -- commands -----------------------------------------------------------------

class RunSyncRepositoryCommand(PulpCliCommand):
    """
    Requests an immediate sync for a repository. If the sync begins (it is not
    postponed or rejected), the provided renderer will be used to track its
    progress. The user has the option to exit the progress polling or skip it
    entirely through a flag on the run command.
    """

    def __init__(self, context, renderer):
        super(RunSyncRepositoryCommand, self).__init__('run', DESC_SYNC_RUN, self.run)

        self.context = context
        self.prompt = context.prompt
        self.renderer = renderer

        self.add_option(options.OPTION_REPO_ID)
        self.create_flag('--' + NAME_BACKGROUND, DESC_BACKGROUND)

    def run(self, **kwargs):
        repo_id = kwargs[options.OPTION_REPO_ID.keyword]
        background = kwargs[NAME_BACKGROUND]

        self.prompt.render_title(_('Synchronizing Repository [%(r)s]') % {'r' : repo_id})

        # See if an existing sync is running for the repo. If it is, resume
        # progress tracking.
        existing_sync_tasks = self.context.server.tasks.get_repo_sync_tasks(repo_id).response_body
        task_group_id = tasks.relevant_existing_task_group_id(existing_sync_tasks)

        if task_group_id is not None:
            msg = _('A sync task is already in progress for this repository. ')
            if not background:
                msg += _('Its progress will be tracked below.')
            self.context.prompt.render_paragraph(msg, tag='in-progress')

        else:
            # Trigger the actual sync
            response = self.context.server.repo_actions.sync(repo_id, None)
            sync_task = tasks.sync_task_in_sync_task_group(response.response_body)
            task_group_id = sync_task.task_group_id

        if not background:
            status.display_group_status(self.context, self.renderer, task_group_id)
        else:
            msg = _('The status of this sync can be displayed using the status command.')
            self.context.prompt.render_paragraph(msg, 'background')


class SyncStatusCommand(PulpCliCommand):
    def __init__(self, context, renderer):
        super(SyncStatusCommand, self).__init__('status', DESC_STATUS, self.run)

        self.context = context
        self.prompt = context.prompt
        self.renderer = renderer

        self.add_option(options.OPTION_REPO_ID)

    def run(self, **kwargs):
        pass
