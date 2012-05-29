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

import status
import tasks as task_utils

from pulp.gc_client.framework.extensions import PulpCliCommand

# -- constants ----------------------------------------------------------------

DISTRIBUTOR_ID = 'yum_distributor'

# -- commands -----------------------------------------------------------------

class RunPublishCommand(PulpCliCommand):
    def __init__(self, context, name, description):
        PulpCliCommand.__init__(self, name, description, self.publish)
        self.context = context

        # In the RPM client, there is currently only one distributor for a
        # repository, so we don't need to ask them for the distributor ID (yet).
        self.create_option('--repo-id', _('identifies the repository to publish'), required=True)

        d = 'if specified, the CLI process will end but the publish will continue on '\
            'the server; the progress can be later displayed using the status command'
        self.create_flag('--bg', _(d))

    def publish(self, **kwargs):
        repo_id = kwargs['repo-id']
        foreground = not kwargs['bg']

        self.context.prompt.render_title(_('Publishing Repository [%(r)s]') % {'r' : repo_id})

        # If a publish is taking place, display it's progress instead. Again, we
        # benefit from the fact that there is only one distributor per repo and
        # if that changes in the future we'll need to rethink this.
        existing_publish_tasks = self.context.server.tasks.get_repo_publish_tasks(repo_id).response_body
        if len(existing_publish_tasks) > 0:
            task_id = task_utils.relevant_existing_task_id(existing_publish_tasks)

            msg = _('A publish task is already in progress for this repository. ')
            if foreground:
                msg += _('Its progress will be tracked below.')
            self.context.prompt.render_paragraph(msg)

        else:
            # Trigger the publish call. Eventually the None in the call should
            # be replaced with override options read in from the CLI.
            response = self.context.server.repo_actions.publish(repo_id, DISTRIBUTOR_ID, None)
            task_id = response.response_body.task_id

        if foreground:
            status.display_status(self.context, task_id)
        else:
            msg = 'The status of this publish request can be displayed using the status command.'
            self.context.prompt.render_paragraph(_(msg))

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
        existing_publish_tasks = self.context.server.tasks.get_repo_publish_tasks(repo_id).response_body
        if len(existing_publish_tasks) > 0:
            task_id = task_utils.relevant_existing_task_id(existing_publish_tasks)

            msg = 'A publish task is queued on the server. Its progress will be tracked below.'
            self.context.prompt.render_paragraph(_(msg))
            status.display_status(self.context, task_id)

        else:
            self.context.prompt.render_paragraph(_('There are no publish tasks currently queued in the server.'))
