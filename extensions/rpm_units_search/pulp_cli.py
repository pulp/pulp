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

from pulp.gc_client.framework.extensions import PulpCliCommand, PulpCliOptionGroup, PulpCliOption

TYPE_RPM = 'rpm'
TYPE_SRPMS = 'srpm'
TYPE_ERRATUM = 'erratum'

def initialize(context):

    if not context.extension_config.getboolean('main', 'enabled'):
        return

    repo_section = context.cli.find_section('repo')
    old_units_command = repo_section.remove_command('units')

    # This is temporary for debugging purposes so I can get access to it
    old_units_command.name = 'gc-units'
    repo_section.add_command(old_units_command)

    units_section = repo_section.create_subsection('units', 'list/search for RPM-related content in a repository')
    units_section.add_command(RpmsCommand(context))

# -- commands -----------------------------------------------------------------

class RpmsCommand(PulpCliCommand):
    def __init__(self, context):
        PulpCliCommand.__init__(self, 'rpm', 'list/search RPMs. SRPMs, and DRPMs', self.search)
        self.context = context

        # Groups
        required_group = PulpCliOptionGroup('Required')
        d = 'all of the following will be assembled into a query with "and" semantics'
        metadata_group = PulpCliOptionGroup('Unit Metadata', d)

        d = 'all of the following will be assembled into a query with "and" semantics'
        association_group = PulpCliOptionGroup('Unit Association Metadata', d)

        self.add_option_group(required_group)
        self.add_option_group(metadata_group)
        self.add_option_group(association_group)

        # Required Group
        required_group.add_option(PulpCliOption('--id', 'identifies the repository to search within', required=True))


    def search(self, **kwargs):
        pass