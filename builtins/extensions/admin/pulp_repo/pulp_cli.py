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

from pulp.client.commands.criteria import CriteriaCommand
from pulp.client.commands.repo import cudl as repo_commands
from pulp.client.commands.repo import group  as group_commands
from pulp.client.extensions.extensions import PulpCliSection, PulpCliCommand, PulpCliOption, UnknownArgsParser

# -- framework hook -----------------------------------------------------------

def initialize(context):
    repo_section = RepoSection(context)
    context.cli.add_section(repo_section)

# -- common options -----------------------------------------------------------

note_desc =  'adds/updates/deletes notes to programmatically identify the resource; '
note_desc += 'key-value pairs must be separated by an equal sign (e.g. key=value); multiple notes can '
note_desc += 'be changed by specifying this option multiple times; notes are deleted by '
note_desc += 'specifying "" as the value'
note_option = PulpCliOption('--note', _(note_desc), required=False, allow_multiple=True)

# -- sections -----------------------------------------------------------------

class RepoSection(PulpCliSection):

    def __init__(self, context):
        """
        @param context:
        @type  context: pulp.client.extensions.core.ClientContext
        """
        PulpCliSection.__init__(self, 'repo', _('repository lifecycle (create, delete, configure, etc.) commands'))

        self.context = context
        self.prompt = context.prompt # for easier access

        self.add_command(repo_commands.CreateRepositoryCommand(context))
        self.add_command(repo_commands.DeleteRepositoryCommand(context))
        self.add_command(repo_commands.UpdateRepositoryCommand(context))
        self.add_command(repo_commands.ListRepositoriesCommand(context))

        # Search Command
        self.add_command(CriteriaCommand(self.search, include_search=True))

        # Subsections
        self.add_subsection(ImporterSection(context))
        self.add_subsection(SyncSection(context))
        self.add_subsection(RepoGroupSection(context))
        self.create_subsection('units', _('list/search for RPM-related content in a repository'))

    def search(self, **kwargs):
        repo_list = self.context.server.repo_search.search(**kwargs)
        for repo in repo_list:
            self.prompt.render_document(repo)

    def units(self, **kwargs):
        repo_id = kwargs['repo-id']
        self.prompt.render_title('Units in Repository [%s]' % repo_id)

        query = {}
        units = self.context.server.repo_unit_search.search(repo_id, query)

        def header_func(i):
            return '-----------'
        filters = ['unit_type_id', 'unit_id', 'owner_type', 'owner_id', 'created', 'updated', 'repo_id', 'metadata']
        order = filters
        self.prompt.render_document_list(units.response_body, header_func=header_func, filters=filters, order=order)

class ImporterSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(self, 'importer', _('manage importers for existing repositories'))
        self.context = context
        self.prompt = context.prompt

        # Add Importer Command
        required_options = [
            ('--id', _('identifies the repository')),
            ('--type_id', _('identifies the type of importer being added')),
        ]
        add_parser = UnknownArgsParser(self.prompt, 'repo add', required_options)
        self.add_command(PulpCliCommand('add', _('adds an importer to a repository'), self.add_importer, parser=add_parser))

    def add_importer(self, **kwargs):
        repo_id = kwargs.pop('id')
        importer_type_id = kwargs.pop('type_id')

        # Everything left in kwargs is considered part of the importer config
        self.context.server.repo_importer.create(repo_id, importer_type_id, kwargs)
        self.prompt.render_success_message('Successfully added importer of type [%s] to repository [%s]' % (importer_type_id, repo_id))

class SyncSection(PulpCliSection):

    def __init__(self, context):
        PulpCliSection.__init__(self, 'sync', _('run, schedule, or view the status of sync operations'))
        self.context = context
        self.prompt = context.prompt

        # Run an Immediate Sync
        run_command = PulpCliCommand('run', _('triggers an immediate sync of a specific repository'), self.run)
        run_command.add_option(PulpCliOption('--id', _('identifies the repository to sync'), required=True))
        self.add_command(run_command)

        # TODO: Add sync schedule and status commands

    def run(self, **kwargs):

        repo_id = kwargs['id']
        self.prompt.render_paragraph('Synchronizing repository [%s]' % repo_id)

        spinner = self.prompt.create_threaded_spinner()
        spinner.start()
        try:
            # TODO: Replace with unknown arg parsing and allow for sync override config
            self.context.server.repo_actions.sync(repo_id, None)
        finally:
            spinner.stop()

        self.prompt.render_success_message('Repository sync completed for repository [%s]' % repo_id)


class RepoGroupMemberSection(PulpCliSection):
    def __init__(self, context):
        super(RepoGroupMemberSection, self).__init__('members', _('manage members of repository groups'))
        self.context = context
        self.prompt = context.prompt

        self.add_command(group_commands.ListRepositoryGroupMembersCommand(context))
        self.add_command(group_commands.AddRepositoryGroupMembersCommand(context))
        self.add_command(group_commands.RemoveRepositoryGroupMembersCommand(context))


class RepoGroupSection(PulpCliSection):
    def __init__(self, context):
        PulpCliSection.__init__(self, 'group', _('repository group commands'))

        self.context = context
        self.prompt = context.prompt # for easier access

        self.add_subsection(RepoGroupMemberSection(context))

        self.add_command(group_commands.CreateRepositoryGroupCommand(context))
        self.add_command(group_commands.UpdateRepositoryGroupCommand(context))
        self.add_command(group_commands.DeleteRepositoryGroupCommand(context))
        self.add_command(group_commands.ListRepositoryGroupsCommand(context))
        self.add_command(group_commands.SearchRepositoryGroupsCommand(context))
