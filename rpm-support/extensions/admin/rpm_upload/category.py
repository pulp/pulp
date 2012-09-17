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

from pulp.client.commands.options import OPTION_REPO_ID
from pulp.client.commands.repo.upload import UploadCommand
from pulp.client.extensions.extensions import PulpCliOption

from pulp_rpm.common.ids import TYPE_ID_PKG_CATEGORY


NAME = 'category'
DESC = _('creates a new package category')

d = _('id of the package category')
OPT_CATEGORY_ID = PulpCliOption('--category-id', d, aliases=['-i'], required=True)

d = _('name of the package category')
OPT_NAME = PulpCliOption('--name', d, aliases=['-n'], required=True)

d = _('description of the package category')
OPT_DESCRIPTION = PulpCliOption('--description', d, aliases=['-d'], required=True)

d = _('display order for the package category')
OPT_ORDER = PulpCliOption('--display-order', d, allow_multiple=False, required=False, default=0)

d = _('package group IDs to include in the package category; multiple may '
      'be indicated by specifying the argument multiple times')
OPT_GROUP = PulpCliOption('--group', d, aliases=['-g'], allow_multiple=True, required=False)


class CreatePackageCategoryCommand(UploadCommand):
    """
    Handles the creation of a package category.
    """

    def __init__(self, context, upload_manager, name=NAME, description=DESC):
        super(CreatePackageCategoryCommand, self).__init__(context, upload_manager,
                                                           name, description,
                                                           upload_files=False)

        self.add_option(OPT_CATEGORY_ID)
        self.add_option(OPT_NAME)
        self.add_option(OPT_DESCRIPTION)
        self.add_option(OPT_ORDER)
        self.add_option(OPT_GROUP)

    def determine_type_id(self, filename, **kwargs):
        return TYPE_ID_PKG_CATEGORY

    def generate_unit_key(self, filename, **kwargs):
        repo_id = kwargs[OPTION_REPO_ID.keyword]
        cat_id = kwargs[OPT_CATEGORY_ID.keyword]
        unit_key = {'id' : cat_id, 'repo_id' : repo_id}
        return unit_key

    def generate_metadata(self, filename, **kwargs):
        name = kwargs[OPT_NAME.keyword]
        description = kwargs[OPT_DESCRIPTION.keyword]
        display_order = kwargs[OPT_ORDER.keyword]
        packagegroupids = kwargs[OPT_GROUP.keyword]

        metadata = {
            'name' : name,
            'description' : description,
            'display_order' : display_order,
            'packagegroupids' : packagegroupids,
            'translated_description' : {},
            'translated_name' : '',
        }
        return metadata
