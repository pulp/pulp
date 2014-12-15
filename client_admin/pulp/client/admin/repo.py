from gettext import gettext as _

from pulp.client.commands.repo import cudl as repo_commands
from pulp.client.commands.repo import group as group_commands
from pulp.client.commands.repo import history as history_commands
from pulp.client.extensions.extensions import PulpCliSection


def initialize(context):
    repo_section = RepoSection(context)
    context.cli.add_section(repo_section)


class RepoSection(PulpCliSection):

    def __init__(self, context):
        """
        @param context:
        @type  context: pulp.client.extensions.core.ClientContext
        """
        PulpCliSection.__init__(self, 'repo', _('list repositories and manage repo groups'))

        self.context = context
        self.prompt = context.prompt  # for easier access

        self.add_command(repo_commands.ListRepositoriesCommand(context, include_all_flag=False))

        # Subsections
        self.add_subsection(RepoGroupSection(context))
        self.add_subsection(RepoHistorySection(context))


class RepoGroupSection(PulpCliSection):
    def __init__(self, context):
        PulpCliSection.__init__(self, 'group', _('repository group commands'))

        self.context = context
        self.prompt = context.prompt  # for easier access

        self.add_subsection(RepoGroupMemberSection(context))

        self.add_command(group_commands.CreateRepositoryGroupCommand(context))
        self.add_command(group_commands.UpdateRepositoryGroupCommand(context))
        self.add_command(group_commands.DeleteRepositoryGroupCommand(context))
        self.add_command(group_commands.ListRepositoryGroupsCommand(context))
        self.add_command(group_commands.SearchRepositoryGroupsCommand(context))


class RepoGroupMemberSection(PulpCliSection):
    def __init__(self, context):
        super(RepoGroupMemberSection, self).__init__('members',
                                                     _('manage members of repository groups'))
        self.context = context
        self.prompt = context.prompt

        self.add_command(group_commands.ListRepositoryGroupMembersCommand(context))
        self.add_command(group_commands.AddRepositoryGroupMembersCommand(context))
        self.add_command(group_commands.RemoveRepositoryGroupMembersCommand(context))


class RepoHistorySection(PulpCliSection):
    def __init__(self, context):
        super(RepoHistorySection, self).__init__('history', _('show sync and publish history'))
        self.context = context
        self.prompt = context.prompt

        self.add_command(history_commands.SyncHistoryCommand(context))
        self.add_command(history_commands.PublishHistoryCommand(context))
