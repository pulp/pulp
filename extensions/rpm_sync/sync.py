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
import time

import status

from pulp.gc_client.framework.extensions import PulpCliCommand, PulpCliSection

# -- constants ----------------------------------------------------------------

LOG = None # set by context


# -- sync commands ------------------------------------------------------------

class RunSyncCommand(PulpCliCommand):
    def __init__(self, context):
        PulpCliCommand.__init__(self, 'run', 'triggers an immediate sync of a repository', self.sync)
        self.context = context
        self.prompt = context.prompt # for ease in accessing

        self.create_option('--repo-id', 'identifies the repository to sync', required=True)

    def sync(self, **kwargs):
        repo_id = kwargs['repo-id']
        self.context.prompt.render_title('Synchronizing Repository [%s]' % repo_id)

        # See if an existing sync is running for the repo. If it is, resume
        # progress tracking.
        existing_sync_tasks = self.context.server.tasks.get_repo_sync_tasks(repo_id).response_body
        if len(existing_sync_tasks) > 0:

            # At this point, we have at least one sync task but that doesn't
            # mean it's running yet. It shouldn't, however, be completed as
            # it wouldn't come back in the lookup. That should leave two
            # possibilities: waiting or running.
            #
            # There will only be one running, so that case is easy: if we find
            # a running task start displaying it.
            #
            # If there are no running tasks, the waiting ones are ordered such
            # that the first one will execute next, so use that task ID and
            # start the display process (it will handle waiting accordingly.

            running_tasks = [t for t in existing_sync_tasks if t.is_running()]
            waiting_tasks = [t for t in existing_sync_tasks if t.is_waiting()]

            if len(running_tasks) > 0:
                task_id = running_tasks[0].task_id
            else:
                task_id = waiting_tasks[0].task_id

            msg = 'An existing sync has already been triggered for this repository. '\
                  'Its progress will be tracked below.'
            self.context.prompt.write(_(msg))
            self.context.prompt.render_spacer()

        else:
            # Trigger the actual sync
            response = self.context.server.repo_actions.sync(repo_id, None)
            task_id = response.response_body.task_id

        self.display_status(task_id)

    def display_status(self, task_id):

        response = self.context.server.tasks.get_task(task_id)
        renderer = status.StatusRenderer(self.context)

        m = 'This command may be exited via CTRL+C without affecting the actual sync operation.'
        self.context.prompt.render_paragraph(_(m))

        # Handle the cases where we don't want to honor the foreground request
        if response.response_body.is_rejected():
            announce = _('The request to synchronize repository was rejected')
            description = _('This is likely due to an impending delete request for the repository.')

            self.context.prompt.render_failure_message(announce)
            self.context.prompt.render_paragraph(description)
            return

        if response.response_body.is_postponed():
            a  = 'The request to synchronize the repository was accepted but postponed '\
                 'due to one or more previous requests against the repository. The sync will '\
                 'take place at the earliest possible time.'
            self.context.prompt.render_paragraph(_(a))
            return

        # If we're here, the sync should be running or hopefully about to run
        begin_spinner = self.context.prompt.create_spinner()
        poll_frequency_in_seconds = self.context.client_config.getfloat('output', 'poll_frequency_in_seconds')

        try:
            while not response.response_body.is_completed():
                if response.response_body.is_waiting():
                    begin_spinner.next(_('Waiting to begin'))
                else:
                    renderer.display_report(response.response_body.progress)

                time.sleep(poll_frequency_in_seconds)

                response = self.context.server.tasks.get_task(response.response_body.task_id)

        except KeyboardInterrupt:
            # If the user presses ctrl+C, don't let the error bubble up, just
            # exit gracefully
            return

        # Even after completion, we still want to display the report one last
        # time in case there was no poll between, say, the middle of the
        # package download and when the task itself reports as finished. We
        # don't want to leave the UI in that half-finished state so this final
        # call is to clean up and render the completed report.
        renderer.display_report(response.response_body.progress)

        if response.response_body.was_successful():
            self.context.prompt.render_success_message('Successfully synchronized repository')
        else:
            self.context.prompt.render_failure_message('Error during repository synchronization')
            self.context.prompt.render_failure_message(response.response_body.exception)
