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

from pulp.client.commands.repo import cudl, group

from pulp_puppet.extension.admin import structure
from pulp_puppet.extension.admin import repo

def initialize(context):
    structure.ensure_structure(context.cli)

    repo_section = structure.repo_section(context.cli)
    repo_section.add_command(repo.CreatePuppetRepositoryCommand(context))
    repo_section.add_command(cudl.UpdateRepositoryCommand(context))
    repo_section.add_command(cudl.DeleteRepositoryCommand(context))
    repo_section.add_command(repo.SearchPuppetRepositoriesCommand(context))

    group_section = structure.repo_group_section(context.cli)
    group_section.add_command(group.CreateRepositoryGroupCommand(context))
    group_section.add_command(group.UpdateRepositoryGroupCommand(context))
    group_section.add_command(group.DeleteRepositoryGroupCommand(context))
    group_section.add_command(group.ListRepositoryGroupsCommand(context))

    members_section = structure.repo_group_members_section(context.cli)
    members_section.add_command(group.AddRepositoryGroupMembersCommand(context))
    members_section.add_command(group.RemoveRepositoryGroupMembersCommand(context))
    members_section.add_command(group.ListRepositoryGroupMembersCommand(context))