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

from pulp.client.extensions.core import PulpPrompt
from pulp.client.extensions.extensions import PulpCliOptionGroup, PulpCliOption
from pulp.client.commands.criteria import UnitAssociationCriteriaCommand, UntypedUnitAssociationCriteriaCommand

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
FIELDS_PACKAGE_GROUP = ('id', 'name', 'description', 'mandatory_package_names', 'conditional_package_names',
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

CONTEXT = None # set by initialize

LOG = logging.getLogger(__name__)

# -- plugin hook --------------------------------------------------------------

def initialize(context):

    global LOG
    LOG = context.logger

    global CONTEXT
    CONTEXT = context

    # Replace the generic units command with a full section of commands
    repo_section = context.cli.find_section('repo')
    repo_section.remove_command('units')

    units_section = repo_section.find_subsection('units')
    add_commands(units_section)


def add_commands(units_section):
    m = _('search for units in a repository')
    units_section.add_command(UntypedUnitAssociationCriteriaCommand(all, name='all', description=m))

    m = _('search for RPMs in a repository')
    units_section.add_command(UnitAssociationCriteriaCommand(rpm, name='rpm', description=m))

    m = _('search for SRPMs in a repository')
    units_section.add_command(UnitAssociationCriteriaCommand(srpm, name='srpm', description=m))

    m = _('search for DRPMs in a repository')
    units_section.add_command(UnitAssociationCriteriaCommand(drpm, name='drpm', description=m))

    m = _('search for package groups in a repository')
    units_section.add_command(UnitAssociationCriteriaCommand(package_group, name='package-group', description=m))

    m = _('search for package categories (groups of package groups) in a repository')
    units_section.add_command(UnitAssociationCriteriaCommand(package_category, name='package-category', description=m))

    m = _('list distributions in a repository')
    units_section.add_command(UnitAssociationCriteriaCommand(distribution, name='distribution', description=m))

    m = _('search errata in a repository')
    errata_command = UnitAssociationCriteriaCommand(errata, name='errata', description=m)
    add_erratum_group(errata_command)
    units_section.add_command(errata_command)


def all(**kwargs):
    _content_command(ALL_TYPES, **kwargs)


def rpm(**kwargs):
    def out_func(document, filter=FIELDS_RPM):
        # Inner function to filter rpm fields to display to the end user
        CONTEXT.prompt.render_document(document, filters=filter)
    _content_command([TYPE_RPM], out_func=out_func, **kwargs)


def srpm(**kwargs):
    _content_command([TYPE_SRPM], **kwargs)


def drpm(**kwargs):
    _content_command([TYPE_DRPM], **kwargs)


def package_group(**kwargs):
    _content_command([TYPE_PACKAGE_GROUP], **kwargs)


def package_category(**kwargs):
    _content_command([TYPE_PACKAGE_CATEGORY], **kwargs)


def distribution(**kwargs):
    _content_command([TYPE_DISTRIBUTION], write_distro, **kwargs)


def errata(**kwargs):
    if kwargs['erratum-id'] is None:
        _content_command([TYPE_ERRATUM], write_erratum, **kwargs)
    else:
        # Collect data
        repo_id = kwargs.pop('repo-id')
        erratum_id = kwargs.pop('erratum-id')
        new_kwargs = {
            'repo-id' : repo_id,
            'filters' : {'id' : erratum_id}
        }
        _content_command([TYPE_ERRATUM], write_erratum_detail, **new_kwargs)


def _content_command(type_ids, out_func=None, **kwargs):
    """
    This is a generic command that will perform a search for any type or
    types of content.

    :param type_ids:    list of type IDs that the command should operate on
    :type  type_ids:    list, tuple

    :param out_func:    optional callable to be used in place of
                        prompt.render_document. must accept one dict
    :type  out_func:    callable

    :param kwargs:  CLI options as input by the user and passed in by okaara
    :type  kwargs:  dict
    """
    out_func = out_func or CONTEXT.prompt.render_document

    repo_id = kwargs.pop('repo-id')
    kwargs['type_ids'] = type_ids
    units = CONTEXT.server.repo_unit.search(repo_id, **kwargs).response_body
    for unit in units:
        # show the association only if specifically requested
        if kwargs.get(UnitAssociationCriteriaCommand.ASSOCIATION_FLAG.keyword):
            out_func(unit)
        else:
            out_func(unit['metadata'])


class InvalidCriteria(Exception):
    """
    During parsing of the user supplied arguments, this will indicate a
    malformed set of values. The message in the exception (e[0]) is formatted
    and i18n'ed to be displayed directly to the user.
    """
    pass


def write_erratum(erratum):
    """
    Write an erratum's metadata out.

    :param erratum: one erratum document
    :type  erratum: dict
    """
    CONTEXT.prompt.render_document(erratum['metadata'])


def write_erratum_detail(erratum):
    """
    Write an erratum out in a specially formatted way. It is not known why this
    was originally needed.

    :param erratum: one erratum document
    :type  erratum: dict
    """
    erratum_meta = erratum['metadata']

    CONTEXT.prompt.render_title(_('Erratum: %(e)s') % {'e' : erratum_meta['id']})

    # Reformat the description
    description = erratum_meta['description']
    if description is not None:
        description = ''
        description_pieces = erratum_meta['description'].split('\n\n')
        for index, paragraph in enumerate(description_pieces):
            single_line_paragraph = ''
            for line in paragraph.split('\n'):
                single_line_paragraph += (line + ' ')

            indent = 2
            wrapped = CONTEXT.prompt.wrap((' ' * indent) + single_line_paragraph, remaining_line_indent=indent)

            description += wrapped
            if index < len(description_pieces) - 1:
                description +=  '\n\n'

    # Reformat packages affected
    package_list = ['  %s-%s:%s-%s.%s' % (p['name'], p['epoch'], p['version'], p['release'], p['arch']) for p in erratum_meta['pkglist'][0]['packages']]

    # Reformat reboot flag
    if erratum_meta['reboot_suggested']:
        reboot = _('Yes')
    else:
        reboot = _('No')

    # Reformat the references
    references = ''
    for r in erratum_meta['references']:
        data = {'i' : r['id'],
                't' : r['type'],
                'h' : r['href']}
        line = REFERENCES_TEMPLATE % data
        references += line

    template_data = {
        'id' : erratum_meta['id'],
        'title' : erratum_meta['title'],
        'summary' : erratum_meta['summary'],
        'desc' : description,
        'severity' : erratum_meta['severity'],
        'type' : erratum_meta['type'],
        'issued' : erratum_meta['issued'],
        'updated' : erratum_meta['updated'],
        'version' : erratum_meta['version'],
        'release' : erratum_meta['release'],
        'status' : erratum_meta['status'],
        'reboot' : reboot,
        'pkgs' : '\n'.join(package_list),
        'refs' : references,
    }

    display = SINGLE_ERRATUM_TEMPLATE % template_data
    CONTEXT.prompt.write(display, skip_wrap=True)


def write_distro(distro):
    """
    Write a distro out in a specially formatted way. It is not known why this
    was originally needed.

    :param distro: one distribution document
    :type  distro: dict
    """
    distro_meta = distro['metadata']

    # Distro Metadata
    # id, family, arch, variant, _storage_path

    data = {
        'id'      : distro_meta['id'],
        'family'  : distro_meta['family'],
        'arch'    : distro_meta['arch'],
        'variant' : distro_meta['variant'],
        'path'    : distro_meta['_storage_path'],
    }

    CONTEXT.prompt.write(_('Id:            %(id)s') % data)
    CONTEXT.prompt.write(_('Family:        %(family)s') % data)
    CONTEXT.prompt.write(_('Architecture:  %(arch)s') % data)
    CONTEXT.prompt.write(_('Variant:       %(variant)s') % data)
    CONTEXT.prompt.write(_('Storage Path:  %(path)s') % data)
    CONTEXT.prompt.render_spacer()

    # Files
    # filename, relativepath, checksum, checksumtype, size
    CONTEXT.prompt.write(_('Files:'))
    for f in distro_meta['files']:
        data = {
            'filename' : f['filename'],
            'path'     : f['relativepath'],
            'size'     : f['size'],
            'type'     : f['checksumtype'],
            'checksum' : f['checksum'],
        }

        CONTEXT.prompt.write(_('  Filename:       %(filename)s') % data)
        CONTEXT.prompt.write(_('  Relative Path:  %(path)s') % data)
        CONTEXT.prompt.write(_('  Size:           %(size)s') % data)
        CONTEXT.prompt.write(_('  Checksum Type:  %(type)s') % data)

        checksum = CONTEXT.prompt.wrap(_('  Checksum:       %(checksum)s') % data, remaining_line_indent=18)
        CONTEXT.prompt.write(checksum, skip_wrap=True)
        CONTEXT.prompt.render_spacer()

# -- utility ------------------------------------------------------------------

def add_erratum_group(command):
    """
    Adds the erratum group and all of its options to the given command.
    """
    erratum_group = PulpCliOptionGroup(_('Erratum'))

    m = _('if specified, the full details of an individual erratum are '
          'displayed, and all other options are ignored except for '
          '--repo-id.')
    erratum_group.add_option(PulpCliOption('--erratum-id',m, required=False))
    command.add_option_group(erratum_group)
