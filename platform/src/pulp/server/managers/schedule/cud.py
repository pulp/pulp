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

import copy

from pulp.common.tags import resource_tag

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
        Create a new sync schedule for a given repository using the given importer.
        @param repo_id:
        @param importer_id:
        @param sync_options:
        @param schedule_data:
        @return:
        """

        # validate the input
        self._validate_importer(repo_id, importer_id)
        self._validate_keys(sync_options, _SYNC_OPTION_KEYS)
        if 'schedule' not in schedule_data:
            raise pulp_exceptions.MissingValue(['schedule'])

        # build the sync call request
        sync_manager = managers_factory.repo_sync_manager()
        args = [repo_id]
        kwargs = {'sync_config_override': sync_options['override_config']}
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_UPDATE_OPERATION},
                     dispatch_constants.RESOURCE_REPOSITORY_IMPORTER_TYPE: {importer_id: dispatch_constants.RESOURCE_READ_OPERATION}}
        weight = pulp_config.config.getint('tasks', 'sync_weight')
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
                resource_tag(dispatch_constants.RESOURCE_REPOSITORY_IMPORTER_TYPE, importer_id)]
        call_request = CallRequest(sync_manager.sync, args, kwargs, resources, None, weight, tags, archive=True)

        # schedule the sync
        scheduler = dispatch_factory.scheduler()
        schedule_id = scheduler.add(call_request, **schedule_data)
        importer_manager = managers_factory.repo_importer_manager()
        importer_manager.add_sync_schedule(repo_id, schedule_id)
        return schedule_id

    def update_sync_schedule(self, repo_id, importer_id, schedule_id, sync_options, schedule_data):
        """
        Update an existing sync schedule.
        @param repo_id:
        @param importer_id:
        @param schedule_id:
        @param sync_options:
        @param schedule_data:
        @return:
        """

        # validate the input
        self._validate_importer(repo_id, importer_id)
        schedule_updates = copy.copy(schedule_data)

        # prepare the call request if there are changes to the sync itself
        scheduler = dispatch_factory.scheduler()
        if sync_options:
            report = scheduler.get(schedule_id)
            call_request = report['call_request']
            if 'override_config' in sync_options:
                call_request.kwargs = {'sync_config_override': sync_options['override_config']}
            schedule_updates['call_request'] = call_request

        # update the scheduled sync
        scheduler.update(schedule_id, **schedule_updates)

    def delete_sync_schedule(self, repo_id, importer_id, schedule_id):
        """
        Delete a scheduled sync from a given repository and importer.
        @param repo_id:
        @param importer_id:
        @param schedule_id:
        @return:
        """

        # validate the input
        self._validate_importer(repo_id, importer_id)

        # remove from the scheduler
        scheduler = dispatch_factory.scheduler()
        scheduler.remove(schedule_id)

        # remove from the importer
        importer_manager = managers_factory.repo_importer_manager()
        importer_manager.remove_sync_schedule(repo_id, schedule_id)

    def _validate_importer(self, repo_id, importer_id):
        # make sure the passed in importer id matches the current importer on the repo
        importer_manager = managers_factory.repo_importer_manager()
        importer = importer_manager.get_importer(repo_id)
        if importer_id != importer['id']:
            raise pulp_exceptions.MissingResource(importer=importer_id)

    # publish methods ----------------------------------------------------------

    def create_publish_schedule(self, repo_id, distributor_id, publish_options, schedule_data):
        """
        Create a new scheduled publish for the given repository and distributor.
        @param repo_id:
        @param distributor_id:
        @param publish_options:
        @param schedule_data:
        @return:
        """

        # validate the input
        self._validate_distributor(repo_id, distributor_id)
        self._validate_keys(publish_options, _PUBLISH_OPTION_KEYS)
        if 'schedule' not in schedule_data:
            raise pulp_exceptions.MissingValue(['schedule'])

        # build the publish call
        publish_manager = managers_factory.repo_publish_manager()
        args = [repo_id, distributor_id]
        kwargs = {'publish_config_override': publish_options['override_config']}
        resources = {dispatch_constants.RESOURCE_REPOSITORY_TYPE: {repo_id: dispatch_constants.RESOURCE_UPDATE_OPERATION},
                     dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE: {distributor_id: dispatch_constants.RESOURCE_READ_OPERATION}}
        weight = pulp_config.config.getint('tasks', 'publish_weight')
        tags = [resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
                resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id)]
        call_request = CallRequest(publish_manager.publish, args, kwargs, resources, None, weight, tags, archive=True)

        # schedule the publish
        scheduler = dispatch_factory.scheduler()
        schedule_id = scheduler.add(call_request, **schedule_data)
        distributor_manager = managers_factory.repo_distributor_manager()
        distributor_manager.add_publish_schedule(repo_id, distributor_id, schedule_id)
        return schedule_id

    def update_publish_schedule(self, repo_id, distributor_id, schedule_id, publish_options, schedule_data):
        """
        Update an existing scheduled publish for the given repository and distributor.
        @param repo_id:
        @param distributor_id:
        @param schedule_id:
        @param publish_options:
        @param schedule_data:
        @return:
        """

        # validate the input
        self._validate_distributor(repo_id, distributor_id)
        schedule_updates = copy.copy(schedule_data)

        # prepare the call request if there are changes to the publish itself
        scheduler = dispatch_factory.scheduler()
        if publish_options:
            report = scheduler.get(schedule_id)
            call_request = report['call_request']
            if 'override_config' in publish_options:
                call_request.kwargs = {'publish_config_override': publish_options['override_config']}
            schedule_updates['call_request'] = call_request

        # update the scheduled publish
        scheduler.update(schedule_id, **schedule_updates)

    def delete_publish_schedule(self, repo_id, distributor_id, schedule_id):
        """
        Delete an existing scheduled publish from the given repository and distributor.
        @param repo_id:
        @param distributor_id:
        @param schedule_id:
        @return:
        """

        # validate the input
        self._validate_distributor(repo_id, distributor_id)

        # remove from the scheduler
        scheduler = dispatch_factory.scheduler()
        scheduler.remove(schedule_id)

        # remove from the distributor
        dispatch_manager = managers_factory.repo_distributor_manager()
        dispatch_manager.remove_publish_schedule(repo_id, distributor_id, schedule_id)

    def _validate_distributor(self, repo_id, distributor_id):
        distributor_manager = managers_factory.repo_distributor_manager()
        distributor_manager.get_distributor(repo_id, distributor_id)

    # utility methods ----------------------------------------------------------

    def _validate_keys(self, options, valid_keys, all_required=False):
        invalid_keys = []
        for key in options:
            if key not in valid_keys:
                invalid_keys.append(key)
        if invalid_keys:
            raise pulp_exceptions.InvalidValue(invalid_keys)
        if not all_required:
            return
        missing_keys = []
        for key in valid_keys:
            if key not in options:
                missing_keys.append(key)
        if missing_keys:
            raise pulp_exceptions.MissingValue(missing_keys)

