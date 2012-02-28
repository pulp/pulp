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

from pulp.gc_client.api.repository import *
from pulp.gc_client.api.server_info import ServerInfoAPI

class Bindings(object):
    def __init__(self, pulp_connection):

        # Please keep the following in alphabetical order to ease reading

        self.repo = RepositoryAPI(pulp_connection)
        self.repo_importer = RepositoryImporterAPI(pulp_connection)
        self.repo_distributor = RepositoryDistributorAPI(pulp_connection)
        self.repo_history = RepositoryHistoryAPI(pulp_connection)
        self.repo_actions = RepositoryActionsAPI(pulp_connection)
        self.repo_search = RepositoryUnitSearchAPI(pulp_connection)

        self.server_info = ServerInfoAPI(pulp_connection)