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

"""
Handles calls to the server that query the plugin and type capabilities.
"""

from pulp.gc_client.api.base import PulpAPI

class ServerInfoAPI(PulpAPI):
    def __init__(self, pulp_connection):
        super(ServerInfoAPI, self).__init__(pulp_connection)
        self.base_path = 'v2/plugins/'

    def get_types(self):
        """
        Returns the list and descriptions of all content types installed on
        the server.

        @return: Response
        """
        path = self.base_path + 'types/'
        return self.server.GET(path)

    def get_importers(self):
        """
        Returns the list and descriptions of all importer types installed
        on the server.

        @return: Response
        """
        path = self.base_path + 'importers/'
        return self.server.GET(path)

    def get_distributors(self):
        """
        Returns the list and descriptions of all distributor types installed
        on the server.

        @return: Response
        """
        path = self.base_path + 'distributors/'
        return self.server.GET(path)

    def ping(self):
        """
        Retrieves basic status information from the server.

        @return: Response
        """
        path = '/v2/services/status/'
        return self.server.GET(path)