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

# Ordering of metadata fields in each type. Keep in mind these are the display
# ordering within a unit; the order of the units themselves in the returned
# list from the server is dictated by the --ascending/--descending options.
ORDER_RPM = ['name', 'epoch', 'version', 'release', 'arch']
ORDER_ERRATA = ['id', 'tite', 'summary', 'severity', 'type', 'description']

# Used to lookup the right order list based on type
ORDER_BY_TYPE = {
    TYPE_RPM : ORDER_RPM,
    TYPE_SRPM : ORDER_RPM,
    TYPE_DRPM : ORDER_RPM,
    TYPE_ERRATUM : ORDER_ERRATA,
}

SINGLE_ERRATUM_TEMPLATE = '''Id:                %(id)s
Title:             %(title)s
Summary:           %(summary)s
Description:
%(desc)s

Severity:          %(severity)s
Type:              %(type)s
Issued:            %(issued)s
Updated:           %(updated)s
Version:           %(version)s
Release:           %(release)s
Status:            %(status)s
Reboot Suggested:  %(reboot)s

Packages Affected:
%(pkgs)s

References:
%(refs)s
'''

REFERENCES_TEMPLATE = '''  ID:   %(i)s
  Type: %(t)s
  Link: %(h)s

'''

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
    errata_command = ErrataCommand(context)

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
        required_group.add_option(PulpCliOption('--repo_id', 'identifies the repository to search within', required=True))
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
        repo_id = kwargs.pop('repo_id')

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
            order = None
            if len(self.type_ids) == 1:
                order = ORDER_BY_TYPE[self.type_ids[0]]
            self.context.prompt.render_document_list(units, order=order)
        else:
            self.context.prompt.render_paragraph(_('No units found'))


class ErrataCommand(PulpCliCommand):
    """
    Handles the display of both the list of errata in the repository as well
    as the details of an individual erratum.
    """

    def __init__(self, context):
        PulpCliCommand.__init__(self, 'errata', _('search errata in a repository'), self.run)
        self.context = context

        # Groups
        required_group = PulpCliOptionGroup('Required')
        erratum_group = PulpCliOptionGroup('Erratum')
        display_group = PulpCliOptionGroup('Display')
        pagination_group = PulpCliOptionGroup('Pagination')

        # Required Group
        required_group.add_option(PulpCliOption('--repo_id', 'identifies the repository to search within', required=True))
        self.add_option_group(required_group)

        # Erratum Group
        erratum_group.add_option(PulpCliOption('--erratum_id', 'if specified, the full details of an individual erratum are displayed', required=False))
        self.add_option_group(erratum_group)

        # Display Group

        #   Cannot scope these fields when searching for more than one type
        d  = 'comma-separated list of fields to include for each erratum; if unspecified all of the following will be displayed; '
        d += 'valid fields: %(f)s'
        description = _(d) % {'f' : ', '.join(FIELDS_ERRATA)}

        display_group.add_option(PulpCliOption('--fields', description, aliases=['-f'], required=False, default=','.join(FIELDS_ERRATA)))
        display_group.add_option(PulpCliOption('--ascending', 'comma-separated list of fields to sort ascending; the order of the fields determines the order priority', aliases=['-a'], required=False))
        display_group.add_option(PulpCliOption('--descending', 'comma-separated list of fields to sort descending; ignored if --ascending is specified', aliases=['-d'], required=False))
        self.add_option_group(display_group)

        # Pagination Group
        pagination_group.add_option(PulpCliOption('--limit', 'maximum number of results to display', aliases=['-l'], required=False))
        pagination_group.add_option(PulpCliOption('--skip', 'number of results to skip', aliases=['-s'], required=False))
        self.add_option_group(pagination_group)

    def run(self, **kwargs):
        """
        Invoked method for the command. This call determines which functionality
        method to run based on if an individual erratum is being requested or
        the full list.
        """

        if kwargs['erratum_id'] is None:
            self.list(**kwargs)
        else:
            self.details(**kwargs)

    def list(self, **kwargs):
        """
        Lists all errata in the repository, applying the necessary criteria.
        """
        repo_id = kwargs.pop('repo_id')

        self.context.prompt.render_title(_('Repository Errata'))

        try:
            criteria = args_to_criteria_doc(kwargs, [TYPE_ERRATUM])
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
            self.context.prompt.render_document_list(units, order=ORDER_ERRATA)
        else:
            self.context.prompt.render_paragraph(_('No units found'))


    def details(self, **kwargs):
        """
        Displays the details of an individual erratum.
        """
        repo_id = kwargs.pop('repo_id')
        erratum_id = kwargs.pop('erratum_id')

        criteria = {
            'type_ids' : [TYPE_ERRATUM],
            'filters' : {
                'unit' : {'id' : erratum_id}
            }
        }

        errata = self.context.server.repo_search.search(repo_id, criteria).response_body

        if len(errata) is 0:
            self.context.prompt.render_paragraph(_('No erratum with ID [%(e)s] found') % {'e' : erratum_id})
        else:
            self.context.prompt.render_title(_('Erratum: %(e)s') % {'e' : erratum_id})

            erratum = errata[0]['metadata']

            # Reformat the description
            description = erratum['description']
            if description is not None:
                description = ''
                description_pieces = erratum['description'].split('\n\n')
                for index, paragraph in enumerate(description_pieces):
                    single_line_paragraph = ''
                    for line in paragraph.split('\n'):
                        single_line_paragraph += (line + ' ')

                    indent = 2
                    wrapped = self.context.prompt.wrap((' ' * indent) + single_line_paragraph, remaining_line_indent=indent)

                    description += wrapped
                    if index < len(description_pieces) - 1:
                        description +=  '\n\n'

            # Reformat packages affected
            package_name_list = ['  ' + p['name'] for p in erratum['pkglist'][0]['packages']]

            # Reformat reboot flag
            if erratum['reboot_suggested']:
                reboot = _('Yes')
            else:
                reboot = _('No')

            # Reformat the references
            references = ''
            for r in erratum['references']:
                data = {'i' : r['id'],
                        't' : r['type'],
                        'h' : r['href']}
                line = _(REFERENCES_TEMPLATE) % data
                references += line

            template_data = {
                'id' : erratum['id'],
                'title' : erratum['title'],
                'summary' : erratum['summary'],
                'desc' : description,
                'severity' : erratum['severity'],
                'type' : erratum['type'],
                'issued' : erratum['issued'],
                'updated' : erratum['updated'],
                'version' : erratum['version'],
                'release' : erratum['release'],
                'status' : erratum['status'],
                'reboot' : reboot,
                'pkgs' : '\n'.join(package_name_list),
                'refs' : references,
            }

            display = SINGLE_ERRATUM_TEMPLATE % template_data
            self.context.prompt.write(display, skip_wrap=True)



# -- utility ------------------------------------------------------------------

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
        field_names = [f.strip() for f in kwargs['fields'].split(',')] # .strip handles "id, name" case
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

