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

from pulp.gc_client.framework.extensions import PulpCliCommand, PulpCliOptionGroup, PulpCliOption, PulpCliFlag

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
        query_group = PulpCliOptionGroup('Query')
        display_group = PulpCliOptionGroup('Display')
        pagination_group = PulpCliOptionGroup('Pagination')

        self.add_option_group(required_group)
        self.add_option_group(query_group)
        self.add_option_group(display_group)
        self.add_option_group(pagination_group)

        # Required Group
        required_group.add_option(PulpCliOption('--id', 'identifies the repository to search within', required=True))

        # Query Group
        query_group.add_option(PulpCliFlag('--srpms', 'if specified, SRPMs are included in the results'))
        query_group.add_option(PulpCliFlag('--drpms', 'if specified, DRPMs are included in the results'))

        # Display Group
        display_group.add_option(PulpCliOption('--fields', 'comma-separated list of fields to include for each RPM; if unspecified all fields will be displayed', aliases=['-f'], required=False))
        display_group.add_option(PulpCliOption('--ascending', 'comma-separated list of fields to sort ascending; the order of the fields determines the order priority', aliases=['-a'], required=False))
        display_group.add_option(PulpCliOption('--descending', 'comma-separated list of fields to sort descending; ignored if --ascending is specified', aliases=['-d'], required=False))

        # Pagination
        display_group.add_option(PulpCliOption('--limit', 'maximum number of results to display', aliases=['-l'], required=False))
        display_group.add_option(PulpCliOption('--skip', 'number of results to skip', aliases=['-s'], required=False))

    def search(self, **kwargs):
        repo_id = kwargs['id']

        self.context.prompt.render_title('Repository RPMs')


# -- utilities ----------------------------------------------------------------

class InvalidCriteria(Exception) : pass

def args_to_criteria_doc(kwargs):
    """
    Converts the arguments retrieved from the user into a criteria document
    for the associated units call.

    @rtype: dict
    """

    criteria = {}

    # Type IDs
    type_ids = ['rpm']
    if kwargs['srpms']:
        type_ids.append('srpms')
    if kwargs['drpms']:
        type_ids.append('drpms')
    criteria['type_ids'] = type_ids

    # Field Limits
    if kwargs['fields'] is not None:
        field_names = kwargs['fields'].split(',')
        criteria['fields'] = {}
        criteria['fields']['units'] = field_names

    # Sorting
    if kwargs['ascending'] is not None:
        field_names = kwargs['ascending'].split(',')
        criteria['sort'] = {}
        criteria['sort']['units'] = [[f, 'ascending'] for f in field_names]
    elif kwargs['descending'] is not None:
        field_names = kwargs['descending'].split(',')
        criteria['sort'] = {}
        criteria['sort']['units'] = [[f, 'descending'] for f in field_names]

    # Limit & Skip
    if kwargs['limit'] is not None:
        limit = int(kwargs['limit'])
        criteria['limit'] = limit

    if kwargs['skip'] is not None:
        skip = int(kwargs['skip'])
        criteria['skip'] = skip

