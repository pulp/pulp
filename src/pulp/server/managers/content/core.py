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

    def add_content(self, content_type, content_id, content_metadata, content_path):
        pass

    def list_content(self, content_type, db_spec=None, model_fields=None):
        pass

    def update_content(self, content_type, content_id, content_delta):
        pass

    def delete_content(self, content_type, content_id):
        pass
