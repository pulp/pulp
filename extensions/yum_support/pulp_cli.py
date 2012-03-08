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

from pulp.gc_client.framework.extensions import PulpCliCommand, PulpCliOption, PulpCliFlag, PulpCliOptionGroup

def initialize(context):

    # Remove generic commands/sections that we want to override
    repo_section = context.cli.find_section('repo')
    repo_section.remove_command('create')
    repo_section.remove_command('update')
    repo_section.remove_subsection('importer')

    # Add in overridden yum functionality
    repo_section.add_command(YumRepoCreateCommand(context))

def create_repo_options(command):
    """
    Adds options/flags for all repo configuration values (repo, importer, and
    distributor). This is meant to be called for both create and update commands
    to simplify consistency

    @param command: command to add options to
    """

    # Groups
    required_group = PulpCliOptionGroup('Required')
    metadata_group = PulpCliOptionGroup('Metadata', '(optional)')
    throttling_group = PulpCliOptionGroup('Throttling', '(optional)')

    command.add_option_group(required_group)
    command.add_option_group(metadata_group)
    command.add_option_group(throttling_group)

    # Required Options
    required_group.add_option(PulpCliOption('--id', 'uniquely identifies the repository; only alphanumeric, -, and _ allowed', required=True))
    required_group.add_option(PulpCliOption('--feed_url', 'URL of the external source repository to sync', required=True))

    # Metadata Options
    metadata_group.add_option(PulpCliOption('--display_name', 'user-readable display name for the repository', required=False))
    metadata_group.add_option(PulpCliOption('--description', 'user-readable description of the repo\'s contents', required=False))

    # Throttling Options
    throttling_group.add_option(PulpCliOption('--max_speed', 'maximum bandwidth used per download thread, in KB/sec, when synchronizing the repo', required=False))
    throttling_group.add_option(PulpCliOption('--num_threads', 'number of threads that will be used to synchronize the repo', required=False))

# -- command implementations --------------------------------------------------

class YumRepoCreateCommand(PulpCliCommand):
    def __init__(self, context):
        desc = 'creates a new repository that is configured to sync and publish RPM related content'
        PulpCliCommand.__init__(self, 'create', desc, self.create)

        self.context = context

        create_repo_options(self)

    def create(self, **kwargs):
        pass