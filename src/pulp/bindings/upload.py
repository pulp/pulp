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

from pulp.bindings.base import PulpAPI

class UploadAPI(PulpAPI):
    """
    Facade into calls related to content upload and importing into repositories.
    """

    def __init__(self, pulp_connection):
        super(UploadAPI, self).__init__(pulp_connection)

    def initialize_upload(self):
        url = '/v2/content/uploads/'
        return self.server.POST(url)

    def upload_segment(self, upload_id, offset, data):
        url = '/v2/content/uploads/%s/%s/' % (upload_id, offset)
        return self.server.PUT(url, data)

    def list_all_uploads(self):
        url = '/v2/content/uploads/'
        return self.server.GET(url)

    def delete_upload(self, upload_id):
        url = '/v2/content/uploads/%s/' % upload_id
        return self.server.DELETE(url)

    def import_upload(self, upload_id, repo_id, unit_type_id, unit_key, unit_metadata):
        url = '/v2/repositories/%s/actions/import_upload/' % repo_id
        body = {
            'upload_id' : upload_id,
            'unit_type_id' : unit_type_id,
            'unit_key' : unit_key,
            'unit_metadata' : unit_metadata,
        }
        return self.server.POST(url, body)