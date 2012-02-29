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

from pulp.gc_client.framework.extensions import PulpCliSection, PulpCliCommand, PulpCliOption, PulpCliFlag

def initialize(context):
    context.cli.add_section(RepoSection(context))

# -- sections -----------------------------------------------------------------

class RepoSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(self, 'repo', 'repository lifecycle (create, delete, configure, etc.) commands')

        self.context = context
        self.prompt = context.prompt # for easier access

        # Create Command
        create_command = PulpCliCommand('create', 'creates a new repository', self.create)
        create_command.add_option(PulpCliOption('--id', 'uniquely identifies the repository; only alphanumeric, -, and _ allowed', required=True))
        create_command.add_option(PulpCliOption('--name', '(optional) user-readable display name for the repository', required=False))
        create_command.add_option(PulpCliOption('--description', '(optional) user-readable description for the repository', required=False))
        self.add_command(create_command)

        # List Command
        list_command = PulpCliCommand('list', 'lists repositories on the Pulp server', self.list)
        list_command.add_option(PulpCliFlag('--summary', 'if specified, only a minimal amount of repository information is displayed'))
        list_command.add_option(PulpCliOption('--fields', 'comma-separated list of repository fields; if specified, only the given fields will displayed', required=False))

        self.add_command(list_command)

    def create(self, **kwargs):

        # Collect input
        id = kwargs['id']
        name = kwargs['name'] or id
        description = kwargs['description']
        notes = None # TODO: add support later

        # Call the server
        self.context.server.repo.create(id, name, description, notes)
        self.prompt.render_success_message('Repository [%s] successfully created' % id)

    def list(self, **kwargs):
        self.prompt.render_title('Repositories')

        repo_list = self.context.server.repo.repositories()

        # Default flags to render_document_list
        filters = None
        order = ['id', 'display_name', 'description', 'content_unit_count']

        if kwargs['summary'] is True:
            filters = ['id', 'display_name']
            order = filters
        elif kwargs['fields'] is not None:
            filters = kwargs['fields'].split(',')
            if 'id' not in filters:
                filters.append('id')
            order = ['id']

        self.prompt.render_document_list(repo_list.response_body, filters=filters, order=order)
