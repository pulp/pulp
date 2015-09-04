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
from pulp.bindings.content import OrphanContentAPI, ContentSourceAPI, ContentCatalogAPI
from pulp.bindings.event_listeners import EventListenerAPI
from pulp.bindings.repo_groups import *
from pulp.bindings.repository import *
from pulp.bindings.consumer_groups import *
from pulp.bindings.consumer import *
from pulp.bindings.server_info import ServerInfoAPI
from pulp.bindings.static import StaticRequest
from pulp.bindings.tasks import TasksAPI, TaskSearchAPI
from pulp.bindings.upload import UploadAPI
from pulp.bindings.auth import *


class Bindings(object):

    def __init__(self, pulp_connection):
        """
        @type:   pulp_connection: pulp.bindings.server.PulpConnection
        """

        # Please keep the following in alphabetical order to ease reading
        self.actions = ActionsAPI(pulp_connection)
        self.bind = BindingsAPI(pulp_connection)
        self.bindings = BindingSearchAPI(pulp_connection)
        self.profile = ProfilesAPI(pulp_connection)
        self.consumer = ConsumerAPI(pulp_connection)
        self.consumer_content = ConsumerContentAPI(pulp_connection)
        self.consumer_content_schedules = ConsumerContentSchedulesAPI(pulp_connection)
        self.consumer_group = ConsumerGroupAPI(pulp_connection)
        self.consumer_group_search = ConsumerGroupSearchAPI(pulp_connection)
        self.consumer_group_actions = ConsumerGroupActionAPI(pulp_connection)
        self.consumer_group_bind = ConsumerGroupBindAPI(pulp_connection)
        self.consumer_group_content = ConsumerGroupContentAPI(pulp_connection)
        self.consumer_history = ConsumerHistoryAPI(pulp_connection)
        self.consumer_search = ConsumerSearchAPI(pulp_connection)
        self.content_orphan = OrphanContentAPI(pulp_connection)
        self.content_source = ContentSourceAPI(pulp_connection)
        self.content_catalog = ContentCatalogAPI(pulp_connection)
        self.event_listener = EventListenerAPI(pulp_connection)
        self.permission = PermissionAPI(pulp_connection)
        self.repo = RepositoryAPI(pulp_connection)
        self.repo_actions = RepositoryActionsAPI(pulp_connection)
        self.repo_distributor = RepositoryDistributorAPI(pulp_connection)
        self.repo_group = RepoGroupAPI(pulp_connection)
        self.repo_group_actions = RepoGroupActionAPI(pulp_connection)
        self.repo_group_distributor = RepoGroupDistributorAPI(pulp_connection)
        self.repo_group_distributor_search = RepoGroupSearchAPI(pulp_connection)
        self.repo_group_search = RepoGroupSearchAPI(pulp_connection)
        self.repo_history = RepositoryHistoryAPI(pulp_connection)
        self.repo_importer = RepositoryImporterAPI(pulp_connection)
        self.repo_publish_schedules = RepositoryPublishSchedulesAPI(pulp_connection)
        self.repo_search = RepositorySearchAPI(pulp_connection)
        self.repo_sync_schedules = RepositorySyncSchedulesAPI(pulp_connection)
        self.repo_unit = RepositoryUnitAPI(pulp_connection)
        self.role = RoleAPI(pulp_connection)
        self.server_info = ServerInfoAPI(pulp_connection)
        self.static = StaticRequest(pulp_connection)
        self.tasks = TasksAPI(pulp_connection)
        self.tasks_search = TaskSearchAPI(pulp_connection)
        self.uploads = UploadAPI(pulp_connection)
        self.user = UserAPI(pulp_connection)
        self.user_search = UserSearchAPI(pulp_connection)
