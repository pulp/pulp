# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http : //www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from gettext import gettext as _

from pulp.client.commands.options import OPTION_REPO_ID
from pulp.client.commands.repo.upload import UploadCommand
from pulp.client.extensions.extensions import PulpCliFlag, PulpCliOption

from pulp_rpm.common.ids import TYPE_ID_PKG_GROUP


NAME = 'group'
DESC = _('creates a new package group')

d = _('id of the package group')
OPT_GROUP_ID = PulpCliOption('--group-id', d, aliases=['-i'], required=True)

d = _('name of the package group')
OPT_NAME = PulpCliOption('--name', d, aliases=['-n'], required=True)

d = _('description of the package group')
OPT_DESCRIPTION = PulpCliOption('--description', d, aliases=['-d'], required=True)

d = _('conditional package name to include in the package group, specified as '
      '"pkg_name : required_package"; multiple may '
      'be indicated by specifying the argument multiple times')
OPT_CONDITIONAL_NAME = PulpCliOption('--cond-name', d, allow_multiple=True, required=False)

d = _('mandatory package name to include in the package group; multiple may '
      'be indicated by specifying the argument multiple times')
OPT_MANDATORY_NAME = PulpCliOption('--mand-name', d, allow_multiple=True, required=False)

d = _('optional package name to include in the package group; multiple may '
      'be indicated by specifying the argument multiple times')
OPT_OPTIONAL_NAME = PulpCliOption('--opt-name', d, allow_multiple=True, required=False)

d = _('default package name to include in the package group; multiple may '
      'be indicated by specifying the argument multiple times')
OPT_DEFAULT_NAME = PulpCliOption('--default-name', d, aliases=['-p'], allow_multiple=True, required=False)

d = _('display order for the package group')
OPT_DISPLAY_ORDER = PulpCliOption('--display-order', d, allow_multiple=False, required=False, default=0)

d = _('sets the "langonly" attribute for the package group')
OPT_LANGONLY = PulpCliOption('--langonly', d, allow_multiple=False, required=False)

d = _('set "default" flag on package group to True')
OPT_DEFAULT = PulpCliFlag('--default', d)

d = _('set "user_visible" flag on package group to True')
OPT_USER_VISIBLE = PulpCliFlag('--user-visible', d)


class CreatePackageGroupCommand(UploadCommand) :
    """
    Handles the creation of a package group.
    """

    def __init__(self, context, upload_manager, name=NAME, description=DESC):
        super(CreatePackageGroupCommand, self).__init__(context, upload_manager,
                                                        name=name, description=description,
                                                        upload_files=False)

        self.add_option(OPT_GROUP_ID)
        self.add_option(OPT_NAME)
        self.add_option(OPT_DESCRIPTION)
        self.add_option(OPT_CONDITIONAL_NAME)
        self.add_option(OPT_MANDATORY_NAME)
        self.add_option(OPT_OPTIONAL_NAME)
        self.add_option(OPT_DEFAULT_NAME)
        self.add_option(OPT_DISPLAY_ORDER)
        self.add_option(OPT_LANGONLY)
        self.add_option(OPT_DEFAULT)
        self.add_option(OPT_USER_VISIBLE)

    def determine_type_id(self, filename, **kwargs) : 
        return TYPE_ID_PKG_GROUP

    def generate_unit_key(self, filename, **kwargs) : 
        pkg_group_id = kwargs[OPT_GROUP_ID.keyword]
        repo_id = kwargs[OPTION_REPO_ID.keyword]
        unit_key = {'id'  :  pkg_group_id, 'repo_id'  :  repo_id}
        return unit_key

    def generate_metadata(self, filename, **kwargs) : 
        name = kwargs[OPT_NAME.keyword]
        description = kwargs[OPT_DESCRIPTION.keyword]
        mand_names = kwargs[OPT_MANDATORY_NAME.keyword]
        opt_names = kwargs[OPT_OPTIONAL_NAME.keyword]
        default_names = kwargs[OPT_DEFAULT_NAME.keyword]
        display_order = kwargs[OPT_DISPLAY_ORDER.keyword]
        default = kwargs[OPT_DEFAULT.keyword]
        langonly = kwargs[OPT_LANGONLY.keyword]
        user_visible = kwargs[OPT_USER_VISIBLE.keyword]

        # Adjust cond_names, format is key : value1,value2,...
        cond_names = []
        cond_names_raw = kwargs[OPT_CONDITIONAL_NAME.keyword]
        if cond_names_raw:
            for entry in cond_names_raw:
                key, value = entry.split(':')
                cond_names.append((key.strip(), value.strip()))

        metadata = {
            'name' : name,
            'description' : description,
            'mandatory_package_names' : mand_names,
            'optional_package_names' : opt_names,
            'default_package_names' : default_names,
            'conditional_package_names' : cond_names,
            'default' : default,
            'user_visible' : user_visible,
            'langonly' : langonly,
            'display_order' : display_order,
            'translated_description' : {},
            'translated_name' : '',
        }
        return metadata
