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

from pulp.bindings.actions import ActionsAPI
from pulp.bindings.repository import *
from pulp.bindings.consumer import *
from pulp.bindings.server_info import ServerInfoAPI
from pulp.bindings.tasks import TasksAPI
from pulp.bindings.upload import UploadAPI


class Bindings(object):
    
    def __init__(self, pulp_connection):

        # Please keep the following in alphabetical order to ease reading
        self.actions = ActionsAPI(pulp_connection)
        self.bind = BindingsAPI(pulp_connection)
        self.consumer = ConsumerAPI(pulp_connection)
        self.consumer_content = ConsumerContentAPI(pulp_connection)
        self.consumer_history = ConsumerHistoryAPI(pulp_connection)
        self.repo = RepositoryAPI(pulp_connection)
        self.repo_importer = RepositoryImporterAPI(pulp_connection)
        self.repo_distributor = RepositoryDistributorAPI(pulp_connection)
        self.repo_history = RepositoryHistoryAPI(pulp_connection)
        self.repo_actions = RepositoryActionsAPI(pulp_connection)
        self.repo_search = RepositoryUnitSearchAPI(pulp_connection)
        self.repo_publish_schedules = RepositoryPublishSchedulesAPI(pulp_connection)
        self.repo_sync_schedules = RepositorySyncSchedulesAPI(pulp_connection)
        self.repo_unit_associations = RepositoryUnitAssociationAPI(pulp_connection)
        self.server_info = ServerInfoAPI(pulp_connection)
        self.tasks = TasksAPI(pulp_connection)
        self.uploads = UploadAPI(pulp_connection)
