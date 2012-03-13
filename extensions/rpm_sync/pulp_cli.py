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

        self.create_option('--id', 'identifies the repository to sync', required=True)

    def sync(self, **kwargs):
        repo_id = kwargs['id']
        self.context.prompt.render_title('Synchronizing Repository [%s]' % repo_id)

        response = self.context.server.repo_actions.sync(repo_id, None)

        if response.response == 'rejected':
            announce = 'Request to synchronize repository [%s] was rejected' % repo_id
            description = 'This is likely due to an impending delete request for the repository.'

            self.context.prompt.render_failure_message(announce)
            self.context.prompt.render_paragraph(description)

            return

        # The output below is temporary until we can track the sync details
        spinner = self.context.prompt.create_spinner()
        completed_states = ('finished', 'error', 'canceled')
        while response.state not in completed_states:
            message  = 'State: %s\n' % response.state
            spinner.next(message=message)
            time.sleep(.25)

            response = self.context.server.tasks.lookup_async_task(response.task_id)

        if response.state == 'finished':
            self.context.prompt.render_success_message('Successfully synchronized repository [%s]' % repo_id)
        else:
            self.context.prompt.render_failure_message('Error during synchronization of repository [%s]' % repo_id)
            self.context.prompt.render_failure_message(response.exception)
