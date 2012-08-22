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

from pulp.client.extensions.extensions import PulpCliCommand

import status, tasks

# -- commands -----------------------------------------------------------------

class RunSyncCommand(PulpCliCommand):
    def __init__(self, context, name, description):
        PulpCliCommand.__init__(self, name, description, self.sync)
        self.context = context

        self.create_option('--repo-id', _('identifies the repository to sync'), required=True)

        # I originally wrote this when the flag was for foreground. In case we
        # move back to that model, I've left the developer the description already.
        # You're welcome.
        #
        # d = 'if specified, the progress for the sync will be continually displayed ' \
        #     'on screen and the CLI process will not end until it is completed; the ' \
        #    'progress can be viewed later using the status command if this is not specified'

        d = _('if specified, the CLI process will end but the sync will continue on ' \
              'the server; the progress can be later displayed using the status command')
        self.create_flag('--bg', d)

    def sync(self, **kwargs):
        repo_id = kwargs['repo-id']
        foreground = not kwargs['bg']

        self.context.prompt.render_title(_('Synchronizing Repository [%(r)s]') % {'r' : repo_id})

        # See if an existing sync is running for the repo. If it is, resume
        # progress tracking.
        existing_sync_tasks = self.context.server.tasks.get_repo_sync_tasks(repo_id).response_body
        if len(existing_sync_tasks) > 0:
            task_group_id = tasks.relevant_existing_task_group_id(existing_sync_tasks)

            msg = _('A sync task is already in progress for this repository. ')
            if foreground:
                msg += _('Its progress will be tracked below.')
            self.context.prompt.render_paragraph(msg)

        else:
            # Trigger the actual sync
            response = self.context.server.repo_actions.sync(repo_id, None)
            sync_task = tasks.sync_task_in_sync_task_group(response.response_body)
            task_group_id = sync_task.task_group_id

        if foreground:
            status.display_status(self.context, task_group_id=task_group_id)
        else:
            msg = _('The status of this sync can be displayed using the status command.')
            self.context.prompt.render_paragraph(msg)

class StatusCommand(PulpCliCommand):
    def __init__(self, context, name, description):
        PulpCliCommand.__init__(self, name, description, self.status)
        self.context = context

        self.create_option('--repo-id', _('identifies the repository'), required=True)

    def status(self, **kwargs):
        repo_id = kwargs['repo-id']
        self.context.prompt.render_title(_('Repository Status [%(r)s]') % {'r' : repo_id})

        # This looks dumb but the task lookup doesn't know if there are no tasks
        # for a repo v. the repo doesn't exist. We call this to let the not found
        # exception bubble if it's not a valid repo.
        self.context.server.repo.repository(repo_id)

        # Load the existing sync tasks
        existing_sync_tasks = self.context.server.tasks.get_repo_sync_tasks(repo_id).response_body
        if len(existing_sync_tasks) > 0:
            task_group_id = tasks.relevant_existing_task_group_id(existing_sync_tasks)

            msg = _('A sync task is queued on the server. Its progress will be tracked below.')
            self.context.prompt.render_paragraph(msg)
            status.display_status(self.context, task_group_id=task_group_id)

        else:
            self.context.prompt.render_paragraph(_('There are no sync tasks currently queued in the server.'))
