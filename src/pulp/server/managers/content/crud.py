# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


class ContentManager(object):

    def add_content_unit(self, content_type, unit_id, unit_metadata, unit_path):
        pass

    def list_content_units(self, content_type, db_spec=None, model_fields=None):
        pass

    def get_content_unit_keys(self, content_type, unit_ids):
        pass

    def get_content_unit_ids(self, content_type, unit_keys):
        pass

    def get_root_content_dir(self, content_type):
        pass

    def update_content_unit(self, content_type, unit_id, unit_metadata_delta):
        pass

    def remove_content_unit(self, content_type, unit_id):
        pass
