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

from pulp.server import config as pulp_config
from pulp.server import exceptions as pulp_exceptions
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.dispatch.call import CallRequest
from pulp.server.managers import factory as managers_factory


_SYNC_OPTION_KEYS = ('override_config',)
_PUBLISH_OPTION_KEYS = ('override_config',)


class ScheduleManager(object):

    # sync methods -------------------------------------------------------------

    def create_sync_schedule(self, repo_id, importer_id, sync_options, schedule_data):
        """
        Create a new sync schedule for a give repository using the given importer.
        @param repo_id:
        @param importer_id:
        @param sync_options:
        @param schedule_data:
        @return:
        """

        # validate the input
        importer_manager = managers_factory.repo_importer_manager()
        importer = importer_manager.get_importer(repo_id)
        if importer_id != importer['id']:
            raise pulp_exceptions.MissingResource(importer=importer_id)
        self._validate_keys(sync_options, _SYNC_OPTION_KEYS)
        if 'schedule' not in sync_options:
            raise pulp_exceptions.MissingValue(['schedule'])

        # build the sync call request
        sync_manager = managers_factory.repo_sync_manager()
        args = [repo_id]
        kwargs = {'sync_config_override': sync_options['override_config']}
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_UPDATE_OPERATION},
                     dispatch_constants.RESOURCE_REPOSITORY_IMPORTER_TYPE: {importer_id: dispatch_constants.RESOURCE_READ_OPERATION}}
        weight = pulp_config.config.getint('tasks', 'sync_weight')
        tags = [repo_id, importer_id]
        call_request = CallRequest(sync_manager.sync, args, kwargs, resources, weight, tags, archive=True)

        # schedule the sync
        scheduler = dispatch_factory.scheduler()
        schedule_id = scheduler.add(call_request, **schedule_data)
        # TODO: add the schedule_id to the importer
        return schedule_id

    def update_sync_schedule(self, schedule_id, sync_options, schedule_data):
        pass

    def delete_sync_schedule(self, schedule_id):
        pass

    # publish methods ----------------------------------------------------------

    def create_publish_schedule(self, repo_id, distributor_id, publish_options, schedule_data):
        pass

    def update_publish_schedule(self, schedule_id, publish_options, schedule_data):
        pass

    def delete_publish_schedule(self, schedule_id):
        pass

    # utility methods ----------------------------------------------------------

    def _validate_keys(self, options, valid_keys):
        invalid_keys = []
        for key in options:
            if key not in valid_keys:
                invalid_keys.append(key)
        if invalid_keys:
            raise pulp_exceptions.InvalidValue(invalid_keys)

