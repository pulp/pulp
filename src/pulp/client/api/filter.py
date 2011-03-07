# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

from pulp.client.api.base import PulpAPI

class FilterAPI(PulpAPI):
    """
    Connection class to access filter related calls
    """
    def create(self, id, type, description=None, package_list=None):
        data = {"id": id,
                "type": type,
                "description": description,
                "package_list": package_list}
        path = "/filters/"
        return self.server.POST(path, data)[1]

    def delete(self, id):
        path = "/filters/%s/" % id
        return self.server.DELETE(path)[1]

    def clean(self):
        path = "/filters/"
        return self.server.DELETE(path)[1]

    def filters(self):
        path = "/filters/"
        return self.server.GET(path)[1]

    def filter(self, id):
        path = "/filters/%s/" % str(id)
        return self.server.GET(path)[1]
