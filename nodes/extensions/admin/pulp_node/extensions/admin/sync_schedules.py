# -*- coding: utf-8 -*-
# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from gettext import gettext as _

from pulp.client.commands.schedule import (
    DeleteScheduleCommand, ListScheduleCommand, CreateScheduleCommand,
    UpdateScheduleCommand, NextRunCommand, ScheduleStrategy)

from pulp_node import constants
from pulp_node.extensions.admin.options import NODE_ID_OPTION, MAX_BANDWIDTH_OPTION, MAX_CONCURRENCY_OPTION


# -- constants ----------------------------------------------------------------

DESC_LIST = _('list scheduled sync operations')
DESC_CREATE = _('adds a new scheduled sync operation')
DESC_DELETE = _('delete a sync schedule')
DESC_UPDATE = _('updates an existing schedule')
DESC_NEXT_RUN = _('displays the next scheduled sync run for a child node')

# A node sync is considered an update operation on the REST API
SYNC_OPERATION = 'update'


# -- commands -----------------------------------------------------------------

class NodeListScheduleCommand(ListScheduleCommand):
    def __init__(self, context):
        strategy = NodeSyncScheduleStrategy(context)
        super(self.__class__, self).__init__(context, strategy, description=DESC_LIST)
        self.add_option(NODE_ID_OPTION)


class NodeCreateScheduleCommand(CreateScheduleCommand):
    def __init__(self, context):
        strategy = NodeSyncScheduleStrategy(context)
        super(self.__class__, self).__init__(context, strategy, description=DESC_CREATE)
        self.add_option(NODE_ID_OPTION)
        self.add_option(MAX_BANDWIDTH_OPTION)
        self.add_option(MAX_CONCURRENCY_OPTION)


class NodeDeleteScheduleCommand(DeleteScheduleCommand):
    def __init__(self, context):
        strategy = NodeSyncScheduleStrategy(context)
        super(self.__class__, self).__init__(context, strategy, description=DESC_DELETE)
        self.add_option(NODE_ID_OPTION)


class NodeUpdateScheduleCommand(UpdateScheduleCommand):
    def __init__(self, context):
        strategy = NodeSyncScheduleStrategy(context)
        super(self.__class__, self).__init__(context, strategy, description=DESC_UPDATE)
        self.add_option(NODE_ID_OPTION)


class NodeNextRunCommand(NextRunCommand):
    def __init__(self, context):
        strategy = NodeSyncScheduleStrategy(context)
        super(self.__class__, self).__init__(context, strategy, description=DESC_NEXT_RUN)
        self.add_option(NODE_ID_OPTION)


# -- framework classes --------------------------------------------------------

class NodeSyncScheduleStrategy(ScheduleStrategy):

    # See super class for method documentation

    def __init__(self, context):
        super(self.__class__, self).__init__()
        self.context = context
        self.api = context.server.consumer_content_schedules

    def create_schedule(self, schedule, failure_threshold, enabled, kwargs):
        node_id = kwargs[NODE_ID_OPTION.keyword]
        max_bandwidth = kwargs[MAX_BANDWIDTH_OPTION.keyword]
        max_concurrency = kwargs[MAX_CONCURRENCY_OPTION.keyword]
        units = [dict(type_id='node', unit_key=None)]
        options = {
            constants.MAX_DOWNLOAD_BANDWIDTH_KEYWORD: max_bandwidth,
            constants.MAX_DOWNLOAD_CONCURRENCY_KEYWORD: max_concurrency,
        }
        return self.api.add_schedule(
            SYNC_OPERATION,
            node_id,
            schedule,
            units,
            failure_threshold,
            enabled,
            options)

    def delete_schedule(self, schedule_id, kwargs):
        node_id = kwargs[NODE_ID_OPTION.keyword]
        return self.api.delete_schedule(SYNC_OPERATION, node_id, schedule_id)

    def retrieve_schedules(self, kwargs):
        node_id = kwargs[NODE_ID_OPTION.keyword]
        return self.api.list_schedules(SYNC_OPERATION, node_id)

    def update_schedule(self, schedule_id, **kwargs):
        node_id = kwargs.pop(NODE_ID_OPTION.keyword)
        return self.api.update_schedule(SYNC_OPERATION, node_id, schedule_id, **kwargs)
