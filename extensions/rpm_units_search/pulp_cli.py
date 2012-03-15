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

from pulp.gc_client.framework.extensions import PulpCliCommand, PulpCliOptionGroup, PulpCliOption, PulpCliFlag

# -- constants ----------------------------------------------------------------

TYPE_RPM = 'rpm'
TYPE_SRPM = 'srpm'
TYPE_DRPM = 'drpm'
TYPE_ERRATUM = 'erratum'

ALL_TYPES = (TYPE_RPM, TYPE_SRPM, TYPE_DRPM, TYPE_ERRATUM)

LOG = None # set by the context

# -- plugin hook --------------------------------------------------------------

def initialize(context):

    if not context.extension_config.getboolean('main', 'enabled'):
        return

    global LOG
    LOG = context.logger

    repo_section = context.cli.find_section('repo')
    old_units_command = repo_section.remove_command('units')

    # This is temporary for debugging purposes so I can get access to it
    old_units_command.name = 'gc-units'
    repo_section.add_command(old_units_command)

    units_section = repo_section.create_subsection('units', 'list/search for RPM-related content in a repository')

    # Search Commands
    all_command = SingleUnitSearchCommand(context, 'all', _('search for all content in a repository'), _('Repository Units'), ALL_TYPES)
    rpm_command = SingleUnitSearchCommand(context, 'rpm', _('search for RPMs in a repository'), _('Repository RPMs'), [TYPE_RPM])
    srpm_command = SingleUnitSearchCommand(context, 'srpm', _('search for SRPMs in a repository'), _('Repository SRPMs'), [TYPE_SRPM])
    drpm_command = SingleUnitSearchCommand(context, 'drpm', _('search for DRPMs in a repository'), _('Repository DRPMs'), [TYPE_DRPM])
    errata_command = SingleUnitSearchCommand(context, 'errata', _('search errata in a repository'), _('Repository Errata'), [TYPE_ERRATUM])

    units_section.add_command(all_command)
    units_section.add_command(rpm_command)
    units_section.add_command(srpm_command)
    units_section.add_command(drpm_command)
    units_section.add_command(errata_command)

# -- commands -----------------------------------------------------------------

class SingleUnitSearchCommand(PulpCliCommand):

    def __init__(self, context, name, description, title, type_ids):
        PulpCliCommand.__init__(self, name, description, self.search)

        self.context = context
        self.title = title

        if not isinstance(type_ids, (list, tuple)):
            type_ids = [type_ids]
        self.type_ids = type_ids

        # Groups
        required_group = PulpCliOptionGroup('Required')
        display_group = PulpCliOptionGroup('Display')
        pagination_group = PulpCliOptionGroup('Pagination')

        # Required Group
        required_group.add_option(PulpCliOption('--id', 'identifies the repository to search within', required=True))
        self.add_option_group(required_group)

        # Display Group

        #   Cannot scope these fields when searching for more than one type
        if len(self.type_ids) == 1:
            display_group.add_option(PulpCliOption('--fields', 'comma-separated list of fields to include for each RPM; if unspecified all fields will be displayed', aliases=['-f'], required=False))
            display_group.add_option(PulpCliOption('--ascending', 'comma-separated list of fields to sort ascending; the order of the fields determines the order priority', aliases=['-a'], required=False))
            display_group.add_option(PulpCliOption('--descending', 'comma-separated list of fields to sort descending; ignored if --ascending is specified', aliases=['-d'], required=False))
            self.add_option_group(display_group)

        # Pagination Group
        pagination_group.add_option(PulpCliOption('--limit', 'maximum number of results to display', aliases=['-l'], required=False))
        pagination_group.add_option(PulpCliOption('--skip', 'number of results to skip', aliases=['-s'], required=False))
        self.add_option_group(pagination_group)

    def search(self, **kwargs):
        # Data collection
        repo_id = kwargs.pop('id')

        self.context.prompt.render_title(self.title)

        try:
            criteria = args_to_criteria_doc(kwargs, self.type_ids)
            LOG.debug('Criteria for unit search')
            LOG.debug(criteria)
        except InvalidCriteria, e:
            self.context.prompt.render_failure_message(e[0])
            return

        # Query the server
        all_units = self.context.server.repo_search.search(repo_id, criteria).response_body

        # We only care about the unit metadata, not the association stuff, so
        # strip out all the fluff and reduce the list to just the metadata entries
        units = [u['metadata'] for u in all_units]

        if len(units) > 0:
            self.context.prompt.render_document_list(units)
        else:
            self.context.prompt.render_paragraph(_('No units found'))

# -- utilities ----------------------------------------------------------------

class InvalidCriteria(Exception) : pass

def args_to_criteria_doc(kwargs, type_ids):
    """
    Converts the arguments retrieved from the user into a criteria document
    for the associated units call.

    @rtype: dict
    """

    criteria = {}

    # Type IDs
    criteria['type_ids'] = type_ids

    # Field Limits
    if 'fields' in kwargs and kwargs['fields'] is not None:
        field_names = kwargs['fields'].split(',')
        criteria['fields'] = {}
        criteria['fields']['unit'] = field_names

    # Sorting
    if 'ascending' in kwargs and kwargs['ascending'] is not None:
        field_names = kwargs['ascending'].split(',')
        criteria['sort'] = {}
        criteria['sort']['unit'] = [[f, 'ascending'] for f in field_names]
    elif 'descending' in kwargs and kwargs['descending'] is not None:
        field_names = kwargs['descending'].split(',')
        criteria['sort'] = {}
        criteria['sort']['unit'] = [[f, 'descending'] for f in field_names]

    # Limit & Skip
    if kwargs['limit'] is not None:
        try:
            limit = int(kwargs['limit'])
        except:
            raise InvalidCriteria(_('Value for limit must be an integer'))
        criteria['limit'] = limit

    if kwargs['skip'] is not None:
        skip = int(kwargs['skip'])
        criteria['skip'] = skip

    return criteria
