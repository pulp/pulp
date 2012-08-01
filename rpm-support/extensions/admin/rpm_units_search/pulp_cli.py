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
import logging

from pulp.client.extensions.extensions import PulpCliCommand, PulpCliOptionGroup, PulpCliOption

# -- constants ----------------------------------------------------------------

# Must correspond to the IDs in the type definitions
TYPE_RPM = 'rpm'
TYPE_SRPM = 'srpm'
TYPE_DRPM = 'drpm'
TYPE_ERRATUM = 'erratum'
TYPE_DISTRIBUTION = 'distribution'
TYPE_PACKAGE_GROUP = 'package_group'
TYPE_PACKAGE_CATEGORY = 'package_category'

# Intentionally does not include distributions; they should be looked up specifically
ALL_TYPES = (TYPE_RPM, TYPE_SRPM, TYPE_DRPM, TYPE_ERRATUM, TYPE_PACKAGE_GROUP, TYPE_PACKAGE_CATEGORY)

# List of all fields that the user can elect to display for each supported type
FIELDS_RPM = ('arch', 'buildhost', 'checksum', 'checksumtype', 'description',
              'epoch', 'filename', 'license', 'name', 'provides', 'release',
              'requires', 'vendor', 'version')
FIELDS_ERRATA = ('id', 'title', 'summary', 'severity', 'type', 'description')
FIELDS_PACKAGE_GROUP = ('id', 'name', 'description', 'mandatory_package_names', 'conditional_package_names', \
                        'optional_package_names', 'default_package_names', 'user_visible')
FIELDS_PACKAGE_CATEGORY = ('id', 'name', 'description', 'packagegroupids')

# Used when generating the --fields help text so it can be customized by type
FIELDS_BY_TYPE = {
    TYPE_RPM : FIELDS_RPM,
    TYPE_SRPM : FIELDS_RPM,
    TYPE_DRPM : FIELDS_RPM,
    TYPE_ERRATUM : FIELDS_ERRATA,
    TYPE_PACKAGE_GROUP : FIELDS_PACKAGE_GROUP,
    TYPE_PACKAGE_CATEGORY : FIELDS_PACKAGE_CATEGORY,
}

# Ordering of metadata fields in each type. Keep in mind these are the display
# ordering within a unit; the order of the units themselves in the returned
# list from the server is dictated by the --ascending/--descending options.
ORDER_RPM = ['name', 'epoch', 'version', 'release', 'arch']
ORDER_ERRATA = ['id', 'tite', 'summary', 'severity', 'type', 'description']
ORDER_PACKAGE_GROUP = ['id', 'name', 'description', 'default_package_names', 'mandatory_package_names', 'optional_package_names', 'conditional_package_names', 'user_visible']
ORDER_PACKAGE_CATEGORY = ['id', 'name', 'description', 'packagegroupids']

# Used to lookup the right order list based on type
ORDER_BY_TYPE = {
    TYPE_RPM : ORDER_RPM,
    TYPE_SRPM : ORDER_RPM,
    TYPE_DRPM : ORDER_RPM,
    TYPE_ERRATUM : ORDER_ERRATA,
    TYPE_PACKAGE_GROUP : ORDER_PACKAGE_GROUP,
    TYPE_PACKAGE_CATEGORY : ORDER_PACKAGE_CATEGORY,
}

# Format to use when displaying the details of a single erratum
SINGLE_ERRATUM_TEMPLATE = _('''Id:                %(id)s
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

Updated Packages:
%(pkgs)s

References:
%(refs)s
''')

# Renders the references section of an erratum. The spacing within matters so
# be careful when changing it.
REFERENCES_TEMPLATE = _('''  ID:   %(i)s
  Type: %(t)s
  Link: %(h)s

''')

LOG = logging.getLogger(__name__)

# -- plugin hook --------------------------------------------------------------

def initialize(context):

    global LOG
    LOG = context.logger

    # Replace the generic units command with a full section of commands
    repo_section = context.cli.find_section('repo')
    repo_section.remove_command('units')

    units_section = repo_section.create_subsection('units', 'list/search for RPM-related content in a repository')

    # Unit Commands
    all_command = GeneralUnitSearchCommand(context, 'all', _('search for all content in a repository'), _('Repository Units'), ALL_TYPES)
    rpm_command = GeneralUnitSearchCommand(context, 'rpm', _('search for RPMs in a repository'), _('Repository RPMs'), [TYPE_RPM])
    srpm_command = GeneralUnitSearchCommand(context, 'srpm', _('search for SRPMs in a repository'), _('Repository SRPMs'), [TYPE_SRPM])
    drpm_command = GeneralUnitSearchCommand(context, 'drpm', _('search for DRPMs in a repository'), _('Repository DRPMs'), [TYPE_DRPM])
    errata_command = ErrataCommand(context, 'errata', _('search errata in a repository'))
    distro_command = DistributionCommand(context, 'distribution', _('list distributions in a repository'))
    package_group_command = GeneralUnitSearchCommand(context, 'package_group', _('search for package groups in a repository'), _('Package Group Units'), [TYPE_PACKAGE_GROUP])
    package_category_command = GeneralUnitSearchCommand(context, 'package_category', _('search for package categories (groups of package groups) in a repository'), 
            _('Package Category Units'), [TYPE_PACKAGE_CATEGORY])

    units_section.add_command(all_command)
    units_section.add_command(rpm_command)
    units_section.add_command(srpm_command)
    units_section.add_command(drpm_command)
    units_section.add_command(errata_command)
    units_section.add_command(distro_command)
    units_section.add_command(package_group_command)
    units_section.add_command(package_category_command)

# -- commands -----------------------------------------------------------------

class InvalidCriteria(Exception):
    """
    During parsing of the user supplied arguments, this will indicate a
    malformed set of values. The message in the exception (e[0]) is formatted
    and i18n'ed to be displayed directly to the user.
    """
    pass

class GeneralUnitSearchCommand(PulpCliCommand):
    """
    Each instance of this command is scoped to a particular unit type during
    instantiation. The title and type_ids will be used in the usage and output
    to customize this command for that type.

    Multiple types may be specified as well if aggregate searching is desired.
    In that case, this implementation will not configure itself with options
    that are incompatible with searching across types.
    """

    def __init__(self, context, name, description, title, type_ids):
        PulpCliCommand.__init__(self, name, description, self.search)

        self.context = context
        self.title = title

        if not isinstance(type_ids, (list, tuple)):
            type_ids = [type_ids]
        self.type_ids = type_ids

        # Groups and options
        add_required_group(self)

        if len(self.type_ids) == 1:
            # The display group options only apply when dealing with a single
            # type, so don't even add them if we know otherwise
            default_fields = FIELDS_BY_TYPE[self.type_ids[0]]
            add_display_group(self, default_fields)

        add_pagination_group(self)

    def search(self, **kwargs):
        """
        Parses the user arguments and assemble the proper query against the
        requested repo.
        """

        # Data collection
        repo_id = kwargs.pop('repo-id')

        try:
            criteria = args_to_criteria_doc(kwargs, self.type_ids)
            LOG.debug('Criteria for unit search')
            LOG.debug(criteria)
        except InvalidCriteria, e:
            self.context.prompt.render_failure_message(e[0])
            return

        # Title is i18n translated when it's passed in so don't do it here.
        # Put this after the criteria parse in case there's an error in the args.
        self.context.prompt.render_title(self.title)

        # Query the server
        all_units = self.context.server.repo_unit_search.search(repo_id, criteria).response_body

        # We only care about the unit metadata, not the association stuff, so
        # strip out all the fluff and reduce the list to just the metadata entries
        units = [u['metadata'] for u in all_units]

        # Render the results
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

    def __init__(self, context, name, description):
        PulpCliCommand.__init__(self, name, description, self.run)
        self.context = context

        # Add options and groups
        add_required_group(self)
        add_erratum_group(self)
        add_display_group(self, FIELDS_ERRATA)
        add_pagination_group(self)

    def run(self, **kwargs):
        """
        Invoked method for the command. This call determines which functionality
        method to run based on if an individual erratum is being requested or
        the full list.
        """

        if kwargs['erratum-id'] is None:
            self.list(**kwargs)
        else:
            self.details(**kwargs)

    def list(self, **kwargs):
        """
        Lists all errata in the repository, applying the necessary criteria.
        """
        self.context.prompt.render_title(_('Repository Errata'))

        # Collect data
        repo_id = kwargs.pop('repo-id')
        try:
            criteria = args_to_criteria_doc(kwargs, [TYPE_ERRATUM])
            LOG.debug('Criteria for errata search')
            LOG.debug(criteria)
        except InvalidCriteria, e:
            self.context.prompt.render_failure_message(e[0])
            return

        # Query the server
        all_units = self.context.server.repo_unit_search.search(repo_id, criteria).response_body

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
        # Collect data
        repo_id = kwargs.pop('repo-id')
        erratum_id = kwargs.pop('erratum-id')

        criteria = {
            'type_ids' : [TYPE_ERRATUM],
            'filters' : {
                'unit' : {'id' : erratum_id}
            }
        }

        # Query the server
        errata = self.context.server.repo_unit_search.search(repo_id, criteria).response_body

        # Render the results
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
            package_list = ['  %s-%s:%s.%s' % (p['name'], p['epoch'], p['version'], p['arch']) for p in erratum['pkglist'][0]['packages']]

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
                line = REFERENCES_TEMPLATE % data
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
                'pkgs' : '\n'.join(package_list),
                'refs' : references,
            }

            display = SINGLE_ERRATUM_TEMPLATE % template_data
            self.context.prompt.write(display, skip_wrap=True)

class DistributionCommand(PulpCliCommand):

    def __init__(self, context, name, description):
        PulpCliCommand.__init__(self, name, description, self.run)

        self.context = context

        add_required_group(self)

    def run(self, **kwargs):
        self.context.prompt.render_title(_('Repository Distributions'))

        # Collect data
        repo_id = kwargs.pop('repo-id')
        try:
            criteria = args_to_criteria_doc(kwargs, [TYPE_DISTRIBUTION])
            LOG.debug('Criteria for distribution search')
            LOG.debug(criteria)
        except InvalidCriteria, e:
            self.context.prompt.render_failure_message(e[0])
            return

        # Query the server
        all_distros = self.context.server.repo_unit_search.search(repo_id, criteria).response_body

        # For the immediate future, there will be either 0 or 1 distributions,
        # but it's just as easy to loop here
        for d in all_distros:
            distro = d['metadata']

            # Distro Metadata
            # id, family, arch, variant, _storage_path

            data = {
                'id'      : distro['id'],
                'family'  : distro['family'],
                'arch'    : distro['arch'],
                'variant' : distro['variant'],
                'path'    : distro['_storage_path'],
            }

            self.context.prompt.write(_('Id:            %(id)s') % data)
            self.context.prompt.write(_('Family:        %(family)s') % data)
            self.context.prompt.write(_('Architecture:  %(arch)s') % data)
            self.context.prompt.write(_('Variant:       %(variant)s') % data)
            self.context.prompt.write(_('Storage Path:  %(path)s') % data)
            self.context.prompt.render_spacer()

            # Files
            # filename, relativepath, checksum, checksumtype, size
            self.context.prompt.write(_('Files:'))
            for f in distro['files']:
                data = {
                    'filename' : f['filename'],
                    'path'     : f['relativepath'],
                    'size'     : f['size'],
                    'type'     : f['checksumtype'],
                    'checksum' : f['checksum'],
                }

                self.context.prompt.write(_('  Filename:       %(filename)s') % data)
                self.context.prompt.write(_('  Relative Path:  %(path)s') % data)
                self.context.prompt.write(_('  Size:           %(size)s') % data)
                self.context.prompt.write(_('  Checksum Type:  %(type)s') % data)

                checksum = self.context.prompt.wrap(_('  Checksum:       %(checksum)s') % data, remaining_line_indent=18)
                self.context.prompt.write(checksum, skip_wrap=True)
                self.context.prompt.render_spacer()

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

        valid_fields = FIELDS_BY_TYPE[type_ids[0]]
        invalid_fields = [f for f in field_names if f not in valid_fields]
        if len(invalid_fields) > 0:
            raise InvalidCriteria(_('Fields must be chosen from the following list: %(l)s') % {'l' : ', '.join(valid_fields)})

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
    def num_parse(key, gt_limit):
        try:
            num = int(kwargs[key])
        except:
            raise InvalidCriteria(_('Value for %(k)s must be an integer') % {'k' : key})

        if num < gt_limit:
            raise InvalidCriteria(_('Value for %(k)s must be greater than or equal to %(g)s') % {'k' : key, 'g' : gt_limit})

        return num

    if 'limit' in kwargs and kwargs['limit'] is not None:
        limit = num_parse('limit', 1)
        criteria['limit'] = limit

    if 'skip' in kwargs and kwargs['skip'] is not None:
        skip = num_parse('skip', 0)
        criteria['skip'] = skip

    return criteria

def add_required_group(command):
    """
    Adds the required group and all of its options to the given command.
    """
    required_group = PulpCliOptionGroup(_('Required'))
    required_group.add_option(PulpCliOption('--repo-id', _('identifies the repository to search within'), required=True))
    command.add_option_group(required_group)

def add_erratum_group(command):
    """
    Adds the erratum group and all of its options to the given command.
    """
    erratum_group = PulpCliOptionGroup(_('Erratum'))
    erratum_group.add_option(PulpCliOption('--erratum-id', _('if specified, the full details of an individual erratum are displayed'), required=False))
    command.add_option_group(erratum_group)

def add_display_group(command, default_fields):
    """
    Adds the display group and all of its options to the given command.
    """
    d  = 'comma-separated list of fields to include for each unit; if unspecified all of the following will be displayed; '
    d += 'valid fields: %(f)s'
    description = _(d) % {'f' : ', '.join(default_fields)}

    display_group = PulpCliOptionGroup(_('Display'))
    display_group.add_option(PulpCliOption('--fields', description, aliases=['-f'], required=False, default=','.join(default_fields)))
    display_group.add_option(PulpCliOption('--ascending', _('comma-separated list of fields to sort ascending; the order of the fields determines the order priority'), aliases=['-a'], required=False))
    display_group.add_option(PulpCliOption('--descending', _('comma-separated list of fields to sort descending; ignored if --ascending is specified'), aliases=['-d'], required=False))
    command.add_option_group(display_group)

def add_pagination_group(command):
    """
    Adds the pagination group and all of its options to the given command.
    """
    pagination_group = PulpCliOptionGroup(_('Pagination'))
    pagination_group.add_option(PulpCliOption('--limit', _('maximum number of results to display'), aliases=['-l'], required=False))
    pagination_group.add_option(PulpCliOption('--skip', _('number of results to skip'), aliases=['-s'], required=False))
    command.add_option_group(pagination_group)
