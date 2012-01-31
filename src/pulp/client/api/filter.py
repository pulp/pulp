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

    def add_packages(self, id, packages):
        addinfo = {'packages': packages}
        path = "/filters/%s/add_packages/" % id
        return self.server.POST(path, addinfo)[1]

    def remove_packages(self, id, packages):
        rminfo = {'packages': packages}
        path = "/filters/%s/remove_packages/" % id
        return self.server.POST(path, rminfo)[1]
