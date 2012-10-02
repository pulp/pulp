# Copyright (c) 2012 Red Hat, Inc.
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

from pulp.client.extensions.extensions import PulpCliOptionGroup, PulpCliOption
from pulp.client.commands.criteria import UnitAssociationCriteriaCommand

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

LOG = logging.getLogger(__name__)

# -- constants ----------------------------------------------------------------

DESC_RPMS = _('search for RPMs in a repository')
DESC_SRPMS = _('search for SRPMs in a repository')
DESC_DRPMS = _('search for DRPMs in a repository')
DESC_GROUPS = _('search for package groups in a repository')
DESC_CATEGORIES = _('search for package categories (groups of package groups) in a repository')
DESC_DISTRIBUTIONS = _('list distributions in a repository')
DESC_ERRATA = _('search errata in a repository')

# -- commands -----------------------------------------------------------------

class SearchRpmsCommand(UnitAssociationCriteriaCommand):

    def __init__(self, context):
        super(SearchRpmsCommand, self).__init__(self.rpm, name='rpm',
                                                description=DESC_RPMS)
        self.context = context

    def rpm(self, **kwargs):

        # This inner function breaks the --details support. I don't have time to
        # deal with it right now, so I filed a bug to address revisiting this
        # entire module as a whole and address it then (860693).
        # jdob, Sep 26, 2012

        def out_func(document_list, filter=FIELDS_RPM):
            # Inner function to filter rpm fields to display to the end user
            self.context.prompt.render_document_list(document_list, filters=filter)
        _content_command(self.context, [TYPE_RPM], out_func=out_func, **kwargs)


class SearchSrpmsCommand(UnitAssociationCriteriaCommand):

    def __init__(self, context):
        super(SearchSrpmsCommand, self).__init__(self.srpm, name='srpm',
                                                 description=DESC_SRPMS)
        self.context = context

    def srpm(self, **kwargs):
        _content_command(self.context, [TYPE_SRPM], **kwargs)


class SearchDrpmsCommand(UnitAssociationCriteriaCommand):

    def __init__(self, context):
        super(SearchDrpmsCommand, self).__init__(self.drpm, name='drpm',
                                                 description=DESC_DRPMS)
        self.context = context

    def drpm(self, **kwargs):
        _content_command(self.context, [TYPE_DRPM], **kwargs)


class SearchPackageGroupsCommand(UnitAssociationCriteriaCommand):

    def __init__(self, context):
        super(SearchPackageGroupsCommand, self).__init__(self.package_group,
                                                         name='group',
                                                         description=DESC_GROUPS)
        self.context = context

    def package_group(self, **kwargs):
        _content_command(self.context, [TYPE_PACKAGE_GROUP], **kwargs)


class SearchPackageCategoriesCommand(UnitAssociationCriteriaCommand):

    def __init__(self, context):
        super(SearchPackageCategoriesCommand, self).__init__(self.package_category,
                                                             name='category',
                                                             description=DESC_CATEGORIES)
        self.context = context

    def package_category(self, **kwargs):
        _content_command(self.context, [TYPE_PACKAGE_CATEGORY], **kwargs)


class SearchDistributionsCommand(UnitAssociationCriteriaCommand):

    def __init__(self, context):
        super(SearchDistributionsCommand, self).__init__(self.distribution,
                                                         name='distribution',
                                                         description=DESC_DISTRIBUTIONS)
        self.context = context

    def distribution(self, **kwargs):
        _content_command(self.context, [TYPE_DISTRIBUTION], self.write_distro, **kwargs)

    def write_distro(self, distro_list):
        """
        Write a distro out in a specially formatted way. It is not known why this
        was originally needed.

        :param distro_list: list of distribution documents; will be of length 1
        :type  distro_list: list
        """
        distro = distro_list[0]
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

        self.context.prompt.write(_('Id:            %(id)s') % data)
        self.context.prompt.write(_('Family:        %(family)s') % data)
        self.context.prompt.write(_('Architecture:  %(arch)s') % data)
        self.context.prompt.write(_('Variant:       %(variant)s') % data)
        self.context.prompt.write(_('Storage Path:  %(path)s') % data)
        self.context.prompt.render_spacer()

        # Files
        # filename, relativepath, checksum, checksumtype, size
        self.context.prompt.write(_('Files:'))
        for f in distro_meta['files']:
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


class SearchErrataCommand(UnitAssociationCriteriaCommand):

    def __init__(self, context):
        super(SearchErrataCommand, self).__init__(self.errata, name='errata',
                                                  description=DESC_ERRATA)
        self.context = context

        erratum_group = PulpCliOptionGroup(_('Erratum'))

        m = _('if specified, the full details of an individual erratum are '
              'displayed, and all other options are ignored except for '
              '--repo-id.')
        erratum_group.add_option(PulpCliOption('--erratum-id', m, required=False))
        self.add_option_group(erratum_group)

    def errata(self, **kwargs):
        if kwargs['erratum-id'] is None:
            _content_command(self.context, [TYPE_ERRATUM], self.write_erratum, **kwargs)
        else:
            # Collect data
            repo_id = kwargs.pop('repo-id')
            erratum_id = kwargs.pop('erratum-id')
            new_kwargs = {
                'repo-id' : repo_id,
                'filters' : {'id' : erratum_id}
            }
            _content_command(self.context, [TYPE_ERRATUM], self.write_erratum_detail, **new_kwargs)

    def write_erratum(self, erratum_list):
        """
        Write an erratum's metadata out.

        :param erratum_list: list of erratum documents; will be of length 1
        :type  erratum_list: list
        """
        self.context.prompt.render_document(erratum_list[0]['metadata'])

    def write_erratum_detail(self, erratum_list):
        """
        Write an erratum out in a specially formatted way. It is not known why this
        was originally needed.

        :param erratum_list: list one erratum documents; will be of length 1
        :type  erratum_list: list
        """
        erratum = erratum_list[0]
        erratum_meta = erratum['metadata']

        self.context.prompt.render_title(_('Erratum: %(e)s') % {'e' : erratum_meta['id']})

        # Reformat the description
        description = erratum_meta['description']
        if description is not None:
            description = ''
            description_pieces = erratum_meta['description'].split('\n\n')
            for index, paragraph in enumerate(description_pieces):
                single_line_paragraph = paragraph.replace('\n', '')

                indent = 2
                wrapped = self.context.prompt.wrap((' ' * indent) + single_line_paragraph, remaining_line_indent=indent)

                description += wrapped
                if index < len(description_pieces) - 1:
                    description +=  '\n\n'

        # Reformat packages affected
        package_list = ['  %s-%s:%s-%s.%s' % (p['name'], p['epoch'], p['version'], p['release'], p['arch'])
                        for p in erratum_meta['pkglist'][0]['packages']]

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
        self.context.prompt.write(display, skip_wrap=True)

# -- utility ------------------------------------------------------------------

def _content_command(context, type_ids, out_func=None, **kwargs):
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
    out_func = out_func or context.prompt.render_document_list

    repo_id = kwargs.pop('repo-id')
    kwargs['type_ids'] = type_ids
    units = context.server.repo_unit.search(repo_id, **kwargs).response_body

    if not kwargs.get(UnitAssociationCriteriaCommand.ASSOCIATION_FLAG.keyword):
        units = [u['metadata'] for u in units]

    out_func(units)
