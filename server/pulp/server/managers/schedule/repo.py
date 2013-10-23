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

from pulp.server import exceptions
from pulp.server.db.model.dispatch import ScheduledCall
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.dispatch.call import CallRequest
from pulp.server.itineraries.repo import publish_itinerary, dummy_itinerary
from pulp.server.managers import factory as managers_factory
from pulp.server.managers.schedule import utils


_PUBLISH_OPTION_KEYS = ('override_config',)
_SYNC_OPTION_KEYS = ('override_config',)


class RepoSyncScheduleManager(object):
    @staticmethod
    def list(repo_id, importer_id):
        RepoSyncScheduleManager.validate_importer(repo_id, importer_id)

        schedule_ids = managers_factory.repo_importer_manager().list_sync_schedules(repo_id)
        return utils.get(schedule_ids)

    @staticmethod
    def create(repo_id, importer_id, sync_options, schedule_data):
        """
        Create a new sync schedule for a given repository using the given importer.

        :param repo_id:
        :param importer_id:
        :param sync_options:
        :param schedule_data:
        :return:    new schedule
        :rtype:     pulp.server.db.model.dispatch.ScheduledCall
        """
        # validate the input
        RepoSyncScheduleManager.validate_importer(repo_id, importer_id)
        utils.validate_keys(sync_options, _SYNC_OPTION_KEYS)

        utils.validate_initial_schedule_options(schedule_data)

        # TODO: put sync itinerary here
        task = dummy_itinerary.name
        args = [repo_id]
        kwargs = {'overrides': sync_options['override_config']}
        schedule = ScheduledCall(schedule_data['schedule'], task, args=args, kwargs=kwargs)
        schedule.save()

        managers_factory.repo_importer_manager().add_sync_schedule(repo_id, schedule.id)

        return schedule

    @staticmethod
    def update(repo_id, importer_id, schedule_id, updates):
        """
        Update an existing sync schedule.

        :param repo_id:
        :param importer_id:
        :param schedule_id:
        :param sync_options:
        :param schedule_data:
        :return:
        """
        RepoSyncScheduleManager.validate_importer(repo_id, importer_id)

        if 'override_config' in updates:
            updates['kwargs'] = {'overrides': updates.pop('override_config')}

        utils.validate_updated_schedule_options(updates)

        utils.update(schedule_id, updates)

    @staticmethod
    def delete(repo_id, importer_id, schedule_id):
        """
        Delete a scheduled sync from a given repository and importer.

        :param repo_id:
        :param importer_id:
        :param schedule_id:
        :return:
        """
        # validate the input
        RepoSyncScheduleManager.validate_importer(repo_id, importer_id)

        # remove from the importer
        importer_manager = managers_factory.repo_importer_manager()
        importer_manager.remove_sync_schedule(repo_id, schedule_id)

        # remove from the scheduler
        utils.delete(schedule_id)

    @staticmethod
    def validate_importer(repo_id, importer_id):
        # make sure the passed in importer id matches the current importer on the repo
        importer_manager = managers_factory.repo_importer_manager()
        importer = importer_manager.get_importer(repo_id)
        if importer_id != importer['id']:
            raise exceptions.MissingResource(importer=importer_id)


class RepoPublishScheduleManager(object):
    @staticmethod
    def create(repo_id, distributor_id, publish_options, schedule_data):
        """
        Create a new scheduled publish for the given repository and distributor.

        :param repo_id:
        :param distributor_id:
        :param publish_options:
        :param schedule_data:
        :return:
        """
        # validate the input
        RepoPublishScheduleManager.validate_distributor(repo_id, distributor_id)
        utils.validate_keys(publish_options, _PUBLISH_OPTION_KEYS)

        utils.validate_initial_schedule_options(schedule_data)

        # TODO: put sync itinerary here
        task = dummy_itinerary.name
        args = [repo_id]
        kwargs = {'overrides': publish_options['override_config']}
        schedule = ScheduledCall(schedule_data['schedule'], task, args=args, kwargs=kwargs)
        schedule.save()

        dist_manager = managers_factory.repo_distributor_manager()
        dist_manager.add_publish_schedule(repo_id, distributor_id, schedule.id)

        return schedule

    @staticmethod
    def update(repo_id, distributor_id, schedule_id, updates):
        """
        Update an existing scheduled publish for the given repository and distributor.

        :param repo_id:
        :param distributor_id:
        :param schedule_id:
        :param publish_options:
        :param schedule_data:
        :return:
        """

        RepoPublishScheduleManager.validate_distributor(repo_id, distributor_id)
        if 'override_config' in updates:
            updates['kwargs'] = {'overrides': updates.pop('override_config')}

        utils.validate_updated_schedule_options(updates)

        utils.update(schedule_id, updates)

    @staticmethod
    def delete(repo_id, distributor_id, schedule_id):
        """
        Delete an existing scheduled publish from the given repository and distributor.

        :param repo_id:
        :param distributor_id:
        :param schedule_id:
        :return:
        """
        # validate the input
        RepoPublishScheduleManager.validate_distributor(repo_id, distributor_id)

        # remove from the distributor
        dispatch_manager = managers_factory.repo_distributor_manager()
        dispatch_manager.remove_publish_schedule(repo_id, distributor_id, schedule_id)

        # remove from the scheduler
        utils.delete(schedule_id)

    @staticmethod
    def validate_distributor(repo_id, distributor_id):
        distributor_manager = managers_factory.repo_distributor_manager()
        distributor_manager.get_distributor(repo_id, distributor_id)
