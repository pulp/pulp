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

from pulp.gc_client.api.base import PulpAPI


class ConsumerAPI(PulpAPI):
    """
    Connection class to access consumer specific calls
    """
    def __init__(self, pulp_connection):
        super(ConsumerAPI, self).__init__(pulp_connection)
        self.base_path = "/v2/consumers/"

    def consumers(self):
        path = self.base_path
        return self.server.GET(path)

    def register(self, id, display_name, description, notes):
        path = self.base_path
        repodata = {"id": id,
                    "display_name": display_name,
                    "description": description,
                    "notes": notes,}
        return self.server.POST(path, repodata)

    def consumer(self, id):
        path = self.base_path + ("%s/" % id)
        return self.server.GET(path)

    def unregister(self, id):
        path = self.base_path + "%s/" % id
        return self.server.DELETE(path)

    def update(self, id, delta):
        path = self.base_path + "%s/" % id
        body = {'delta' : delta}
        return self.server.PUT(path, body)
