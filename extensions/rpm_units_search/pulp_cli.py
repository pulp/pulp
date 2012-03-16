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

from pulp.gc_client.framework.extensions import PulpCliCommand, PulpCliOptionGroup, PulpCliOption

# -- constants ----------------------------------------------------------------

TYPE_RPM = 'rpm'
TYPE_SRPM = 'srpm'
TYPE_DRPM = 'drpm'
TYPE_ERRATUM = 'erratum'

ALL_TYPES = (TYPE_RPM, TYPE_SRPM, TYPE_DRPM, TYPE_ERRATUM)

# List of all fields that the user can elect to display for each supported type
FIELDS_RPM = ('arch', 'buildhost', 'checksum', 'checksumtype', 'description',
              'epoch', 'filename', 'license', 'name', 'provides', 'release',
              'requires', 'vendor', 'version')
FIELDS_ERRATA = ('id', 'tite', 'summary', 'severity', 'type', 'description')

# Used when generating the --fields help text so it can be customized by type
FIELDS_BY_TYPE = {
    TYPE_RPM : FIELDS_RPM,
    TYPE_SRPM : FIELDS_RPM,
    TYPE_DRPM : FIELDS_RPM,
    TYPE_ERRATUM : FIELDS_ERRATA,
}

# Ordering of metadata fields in each type
ORDER_RPM = ['name', 'epoch', 'version', 'release', 'arch']
ORDER_ERRATA = ['id', 'tite', 'summary', 'severity', 'type', 'description']

# Used to lookup the right order list based on type
ORDER_BY_TYPE = {

}

LOG = None # set by the context

# -- plugin hook --------------------------------------------------------------

def initialize(context):

    if not context.extension_config.getboolean('main', 'enabled'):
        return

    global LOG
    LOG = context.logger

    # Replace the generic units command with a full section of commands
    repo_section = context.cli.find_section('repo')
    repo_section.remove_command('units')

    units_section = repo_section.create_subsection('units', 'list/search for RPM-related content in a repository')

    # Search Commands
    all_command = GeneralUnitSearchCommand(context, 'all', _('search for all content in a repository'), _('Repository Units'), ALL_TYPES)
    rpm_command = GeneralUnitSearchCommand(context, 'rpm', _('search for RPMs in a repository'), _('Repository RPMs'), [TYPE_RPM])
    srpm_command = GeneralUnitSearchCommand(context, 'srpm', _('search for SRPMs in a repository'), _('Repository SRPMs'), [TYPE_SRPM])
    drpm_command = GeneralUnitSearchCommand(context, 'drpm', _('search for DRPMs in a repository'), _('Repository DRPMs'), [TYPE_DRPM])
    errata_command = GeneralUnitSearchCommand(context, 'errata', _('search errata in a repository'), _('Repository Errata'), [TYPE_ERRATUM])

    units_section.add_command(all_command)
    units_section.add_command(rpm_command)
    units_section.add_command(srpm_command)
    units_section.add_command(drpm_command)
    units_section.add_command(errata_command)

# -- commands -----------------------------------------------------------------

class InvalidCriteria(Exception):
    """
    During parsing of the user supplied arguments, this will indicate a
    malformed set of values. The message in the exception (e[0]) is formatted
    and i18n'ed to be displayed directly to the user.
    """
    pass

class GeneralUnitSearchCommand(PulpCliCommand):

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
            d  = 'comma-separated list of fields to include for each RPM; if unspecified all fields will be displayed; '
            d += 'valid fields: %(f)s'
            description = _(d) % {'f' : ', '.join(FIELDS_BY_TYPE[self.type_ids[0]])}

            display_group.add_option(PulpCliOption('--fields', description, aliases=['-f'], required=False))
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
            criteria = self._args_to_criteria_doc(kwargs, self.type_ids)
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

    def _args_to_criteria_doc(self, kwargs, type_ids):
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

