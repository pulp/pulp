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

# -- framework hook -----------------------------------------------------------

def initialize(context):

    if not context.extension_config.getboolean('main', 'enabled'):
        return

    global LOG
    LOG = context.logger

    # Override the repo sync command
    repo_section = context.cli.find_section('repo')
    sync_section = repo_section.find_subsection('sync')
    sync_section.add_subsection(SchedulingSection(context))
    sync_section.remove_command('run')

    # Add in new commands from this extension
    sync_section.add_command(RunSyncCommand(context))

# -- commands -----------------------------------------------------------------

class RunSyncCommand(PulpCliCommand):
    def __init__(self, context):
        PulpCliCommand.__init__(self, 'run', 'triggers an immediate sync of a repository', self.sync)
        self.context = context
        self.prompt = context.prompt # for ease in accessing

        self.create_option('--repo-id', 'identifies the repository to sync', required=True)


    def sync(self, **kwargs):
        repo_id = kwargs['repo-id']
        self.context.prompt.render_title('Synchronizing Repository [%s]' % repo_id)

        # Trigger the actual sync
        response = self.context.server.repo_actions.sync(repo_id, None)

        self.display_status(response.response_body.task_id)

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
            a  = 'The request to synchronize the repository was accepted but postponed ' \
                 'due to one or more previous requests against the repository. The sync will ' \
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

class SchedulingSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(self, 'schedule', _('repository synchronization scheduling'))
        for Command in (ListScheduled, AddScheduled, DeleteScheduled):
            command = Command(context)
            command.create_option('--repo-id', _('identifies the repository'), required=True)
            self.add_command(command)


class ListScheduled(PulpCliCommand):

    def __init__(self, context):
        PulpCliCommand.__init__(self, 'list', _('list scheduled synchronizations'), self.list)
        self.context = context

    def list(self, **kwargs):
        pass


class AddScheduled(PulpCliCommand):

    def __init__(self, context):
        PulpCliCommand.__init__(self, 'add', _('add a scheduled synchronization'), self.add)
        self.context = context

    def add(self, **kwargs):
        pass


class DeleteScheduled(PulpCliCommand):

    def __init__(self, context):
        PulpCliCommand.__init__(self, 'delete', _('delete a scheduled synchronization'), self.delete)
        self.context = context

    def delete(self, **kwargs):
        pass