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

from pulp.gc_client.framework.extensions import PulpCliCommand

LOG = None # set by context

def initialize(context):

    if not context.extension_config.getboolean('main', 'enabled'):
        return

    global LOG
    LOG = context.logger

    # Override the repo sync command
    repo_section = context.cli.find_section('repo')
    sync_section = repo_section.find_subsection('sync')
    sync_section.remove_command('run')

    # Add in new commands from this extension
    sync_section.add_command(RunSyncCommand(context))

# -- commands -----------------------------------------------------------------

class RunSyncCommand(PulpCliCommand):
    def __init__(self, context):
        PulpCliCommand.__init__(self, 'run', 'triggers an immediate sync of a repository', self.sync)
        self.context = context

        self.create_option('--repo_id', 'identifies the repository to sync', required=True)

    def sync(self, **kwargs):
        repo_id = kwargs['repo_id']
        self.context.prompt.render_title('Synchronizing Repository [%s]' % repo_id)

        # Trigger the actual sync
        response = self.context.server.repo_actions.sync(repo_id, None)

        self._render_status(response.task_id)

    def _render_status(self, task_id):

        response = self.context.server.tasks.get_task(task_id)

        m = 'This command may be exited via CTRL+C without affecting the actual sync operation.'
        self.context.prompt.render_paragraph(_(m))

        # Handle the cases where we don't want to honor the foreground request
        if response.is_rejected():
            announce = _('The request to synchronize repository was rejected')
            description = _('This is likely due to an impending delete request for the repository.')

            self.context.prompt.render_failure_message(announce)
            self.context.prompt.render_paragraph(description)
            return

        if response.is_postponed():
            a  = 'The request to synchronize the repository was accepted but postponed ' \
                 'due to one or more previous requests against the repository. The sync will ' \
                 'take place at the earliest possible time.'
            self.context.prompt.render_paragraph(_(a))
            return

        # If we're here, the sync should be running or hopefully about to run
        spinner = self.context.prompt.create_spinner()
        progress_bar = self.context.prompt.create_progress_bar()
        poll_frequency_in_seconds = self.context.client_config.getfloat('output', 'poll_frequency_in_seconds')

        while not response.is_completed():
            if response.is_waiting():
                spinner.next(_('Waiting to begin'))
            else:
                self._render_progress_bar(response, progress_bar)

            time.sleep(poll_frequency_in_seconds)

            response = self.context.server.tasks.get_task(response.task_id)

        if response.was_successful():
            progress_bar.render(1, 1) # to make it finish out
            self.context.prompt.render_success_message('Successfully synchronized repository')
        else:
            self.context.prompt.render_failure_message('Error during synchronization of repository [%s]' % repo_id)
            self.context.prompt.render_failure_message(response.exception)

    def _render_progress_bar(self, response, progress_bar):
        """
        Analyzes the progress dictionary provided by the importer and updates
        the progress bar accordingly.
        """

        # TODO: handle errors

        message = ''

        if 'step' not in response.progress:
            return

        if response.progress['step'] is not None:
            message += _('Step: %(s)s\n') % {'s' : response.progress['step']}
            if 'Downloading Items' in response.progress['step']:
                items_total = response.progress['items_total']
                items_done = items_total - response.progress['items_left']

                message += _('Total: %(i)s/%(j)s items') % {'i' : items_done,
                                                            'j' : items_total}
            else:
                message += _('Waiting')
        else:
            message += _('Waiting')

        # Bar progress
        if response.progress['size_total'] > 0:
            bar_total = response.progress['size_total']
            bar_done = bar_total - response.progress['size_left']
        else:
            bar_total = 1
            bar_done = 1

        progress_bar.render(bar_done, bar_total, message=message)