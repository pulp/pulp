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

import os

from pulp.client.commands.repo import upload as upload_commands

from pulp_puppet.common import constants
from pulp_puppet.common.model import Module

# -- commands -----------------------------------------------------------------

class UploadModuleCommand(upload_commands.UploadCommand):

    def __init__(self, context, upload_manager):
        super(UploadModuleCommand, self).__init__(context, upload_manager)

    def generate_unit_key(self, filename, **kwargs):
        root_filename = os.path.basename(filename)
        root_filename = root_filename[:-len('.tar.gz')]
        author, name, version = root_filename.split('-')
        unit_key = Module.generate_unit_key(name, version, author)
        return unit_key

    def determine_type_id(self, filename, **kwargs):
        return constants.TYPE_PUPPET_MODULE

    def matching_files_in_dir(self, dir):
        all_files_in_dir = super(UploadModuleCommand, self).matching_files_in_dir(dir)
        modules = [f for f in all_files_in_dir if f.endswith('.tar.gz')]
        return modules