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

from   pulp.client.extensions.extensions import PulpCliCommand
from   pulp_upload.pulp_cli import _upload_manager, _perform_upload

# -- constants ----------------------------------------------------------------
PKG_GROUP_TYPE_ID="package_group"
PKG_CATEGORY_TYPE_ID="package_category"


# -- framework hook -----------------------------------------------------------

def initialize(context):

    repo_section = context.cli.find_section('repo')
    uploads_section = repo_section.find_subsection('uploads')

    d = 'create a package group in a repository'
    uploads_section.add_command(CreatePackageGroupCommand(context, 'group', _(d)))

    d = 'create a package category in a repository'
    uploads_section.add_command(CreatePackageCategoryCommand(context, 'category', _(d)))

# -- commands -----------------------------------------------------------------

class CreatePackageGroupCommand(PulpCliCommand):
    """
    Handles creation of a package group
    """

    def __init__(self, context, name, description):
        PulpCliCommand.__init__(self, name, description, self.create)
        self.context = context
        self.prompt = context.prompt

        d = 'identifies the repository the package group will be created in'
        self.create_option('--repo-id', _(d), required=True)

        d = 'id of this package group'
        self.create_option('--group-id', _(d), aliases=['-i'], required=True)

        d = 'name of this package group'
        self.create_option('--name', _(d), aliases=['-n'], required=True)

        d = 'description of this package group'
        self.create_option('--description', _(d), aliases=['-d'], required=True)

        d = 'conditional package name to include in this package group, specified as "key:value1,value2,..."; multiple may '\
            'be indicated by specifying the argument multiple times'
        self.create_option('--cond-name', _(d), allow_multiple=True, required=False)

        d = 'mandatory package name to include in this package group; multiple may '\
            'be indicated by specifying the argument multiple times'
        self.create_option('--mand-name', _(d), allow_multiple=True, required=False)

        d = 'optional package name to include in this package group; multiple may '\
            'be indicated by specifying the argument multiple times'
        self.create_option('--opt-name', _(d), allow_multiple=True, required=False)

        d = 'default package name to include in this package group; multiple may ' \
            'be indicated by specifying the argument multiple times'
        self.create_option('--default-name', _(d), aliases=['-p'], allow_multiple=True, required=False)

        d = 'display order for this package group'
        self.create_option('--display-order', _(d), allow_multiple=False, required=False, default=0)

        d = 'sets the "langonly" attribute for this package group'
        self.create_option('--langonly', _(d), allow_multiple=False, required=False)

        d = 'set "default" flag on package group to True'
        self.create_flag('--default', _(d))

        d = 'set "user_visible" flag on package group to True'
        self.create_flag('--user-visible', _(d))
        
        d = 'display extra information about the creation process'
        self.create_flag('-v', _(d))

    def create(self, **kwargs):
        self.prompt.render_title(_('Package Group Creation'))

        repo_id = kwargs['repo-id']
        pkg_group_id = kwargs['group-id']
        name = kwargs['name']
        description = kwargs['description']
        #
        # Adjust cond_names
        # format is key:value1,value2,...
        #
        cond_names = {}
        cond_names_raw = kwargs['cond-name']
        if cond_names_raw:
            for entry in cond_names_raw:
                key, values = entry.split(":")
                cond_names[key] = values.split(",")

        mand_names = kwargs['mand-name']
        opt_names = kwargs['opt-name']
        default_names = kwargs['default-name']
        display_order = kwargs['display-order']
        default = kwargs['default']
        langonly = kwargs['langonly']
        user_visible = kwargs['user-visible']

        unit_key = {"id":pkg_group_id, "repo_id":repo_id}
        metadata = {
                "name":name,
                "description":description,
                "mandatory_package_names":mand_names,
                "optional_package_names":opt_names,
                "default_package_names":default_names,
                "conditional_package_names":cond_names,
                "default":default,
                "user_visible":user_visible,
                "langonly":langonly,
                "display_order":display_order,
                "translated_description":{},
                "translated_name":"",
                }

        # Display the list of found RPMs
        if kwargs['v']:
            self.prompt.write(_('Package Group Details:'))

            combined = dict()
            combined.update(unit_key)
            combined.update(metadata)

            self.prompt.render_document(combined, order=['id', 'repo_id'], indent=2)
            self.prompt.render_spacer()

        # Initialize all uploads
        upload_manager = _upload_manager(self.context)
        upload_id = upload_manager.initialize_upload(None, repo_id, PKG_GROUP_TYPE_ID, unit_key, metadata)
        _perform_upload(self.context, upload_manager, [upload_id])

class CreatePackageCategoryCommand(PulpCliCommand):
    """
    Handles creation of a package category
    """

    def __init__(self, context, name, description):
        PulpCliCommand.__init__(self, name, description, self.create)
        self.context = context
        self.prompt = context.prompt

        d = 'identifies the repository the package category will be created in'
        self.create_option('--repo-id', _(d), required=True)

        d = 'id of this package category'
        self.create_option('--category-id', _(d), aliases=['-i'], required=True)

        d = 'name of this package category'
        self.create_option('--name', _(d), aliases=['-n'], required=True)

        d = 'description of this package category'
        self.create_option('--description', _(d), aliases=['-d'], required=True)

        d = 'display order for this package category'
        self.create_option('--display-order', _(d), allow_multiple=False, required=False, default=0)

        d = 'package group ids to include in this package category'
        self.create_option('--package', _(d), aliases=['-p'], allow_multiple=True, required=False)

        d = 'display extra information about the creation process'
        self.create_flag('-v', _(d))

    def create(self, **kwargs):
        self.prompt.render_title(_('Package Category Creation'))
        repo_id = kwargs['repo-id']
        cat_id = kwargs['category-id']
        name = kwargs['name']
        description = kwargs['description']
        display_order = kwargs['display-order']
        packagegroupids = kwargs['package']

        unit_key = {"id":cat_id, "repo_id":repo_id}
        metadata = {
                "name":name,
                "description":description,
                "display_order":display_order,
                "packagegroupids":packagegroupids,
                "translated_description":{},
                "translated_name":"",
                }

        # Display the list of found RPMs
        if kwargs['v']:
            self.prompt.write(_('Package Category Details:'))

            combined = dict()
            combined.update(unit_key)
            combined.update(metadata)

            self.prompt.render_document(combined, order=['id', 'repo_id'], indent=2)
            self.prompt.render_spacer()


        # Initialize all uploads
        upload_manager = _upload_manager(self.context)
        upload_id = upload_manager.initialize_upload(None, repo_id, PKG_CATEGORY_TYPE_ID, unit_key, metadata)
        _perform_upload(self.context, upload_manager, [upload_id])

