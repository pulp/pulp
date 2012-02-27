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

class AdminAuthAPI(PulpAPI):
    """
    Connection class to access repo specific calls
    """
    def __init__(self, pulp_connection):
        super(AdminAuthAPI, self).__init__(pulp_connection)

    def authenticate(self, username, password):
        path = '/users/admin_certificate/'

        self.server.username = username
        self.server.password = password

        return self.server.GET(path)
