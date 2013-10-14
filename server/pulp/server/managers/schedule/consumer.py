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

from celery import task

from pulp.common.tags import action_tag, resource_tag
from pulp.server import exceptions as pulp_exceptions
from pulp.server.async.tasks import Task
from pulp.server.dispatch import constants as dispatch_constants, factory as dispatch_factory
from pulp.server.dispatch.call import CallRequest
from pulp.server.itineraries.consumer import (
    consumer_content_install_itinerary, consumer_content_uninstall_itinerary,
    consumer_content_update_itinerary)
from pulp.server.managers import factory as managers_factory
from pulp.server.managers.schedule import utils as schedule_utils


UNIT_INSTALL_ACTION = 'scheduled_unit_install'
UNIT_UPDATE_ACTION = 'scheduled_unit_update'
UNIT_UNINSTALL_ACTION = 'scheduled_unit_uninstall'
_UNIT_OPTION_KEYS = ('options',)


class ConsumerScheduleManager(object):
    """
    Abstract base class for consumer content management schedules.
    """

    @staticmethod
    def _validate_consumer(consumer_id):
        consumer_manager = managers_factory.consumer_manager()
        consumer_manager.get_consumer(consumer_id)

    @staticmethod
    def _create_schedule(itinerary_method, action_name, consumer_id, units, options,
                         schedule_data):
        ConsumerScheduleManager._validate_consumer(consumer_id)
        schedule_utils.validate_keys(options, _UNIT_OPTION_KEYS)
        if 'schedule' not in schedule_data:
            raise pulp_exceptions.MissingValue(['schedule'])

        args = [consumer_id]
        kwargs = {'units': units,
                  'options': options.get('options', {})}
        tags = [resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id),
                action_tag(action_name)]
        call_request = CallRequest(itinerary_method, args, kwargs, weight=0, tags=tags) # rbarlow_converted

        scheduler = dispatch_factory.scheduler()
        schedule_id = scheduler.add(call_request, **schedule_data)
        return schedule_id

    @staticmethod
    def _update_schedule(consumer_id, schedule_id, units=None, options=None,
                         schedule_data=None):
        ConsumerScheduleManager._validate_consumer(consumer_id)
        schedule_updates = copy.copy(schedule_data) or {}

        scheduler = dispatch_factory.scheduler()
        report = scheduler.get(schedule_id)
        call_request = report['call_request']

        if units is not None:
            call_request.kwargs['units'] = units
            schedule_updates['call_request'] = call_request

        if options is not None and 'options' in options:
            call_request.kwargs['options'] = options['options']
            schedule_updates['call_request'] = call_request

        scheduler.update(schedule_id, **schedule_updates)

    @staticmethod
    def _delete_schedule(consumer_id, schedule_id):
        ConsumerScheduleManager._validate_consumer(consumer_id)

        scheduler = dispatch_factory.scheduler()
        scheduler.remove(schedule_id)

    def _delete_all_schedules(self, management_action_name, consumer_id):
        ConsumerScheduleManager._validate_consumer(consumer_id)

        scheduler = dispatch_factory.scheduler()
        consumer_tag = resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id)
        management_tag = action_tag(management_action_name)
        reports = scheduler.find(consumer_tag, management_tag)

        for r in reports:
            scheduler.remove(r['call_report']['schedule_id'])


class ConsumerContentInstallScheduleManager(ConsumerScheduleManager):
    @staticmethod
    def create_unit_install_schedule(consumer_id, units, install_options, schedule_data ):
        """
        Create a schedule for installing content units on a consumer.
        @param consumer_id: unique id for the consumer
        @param units: list of unit type and unit key dicts
        @param install_options: options to pass to the install manager
        @param schedule_data: scheduling data
        @return: schedule id
        """
        return ConsumerScheduleManager._create_schedule(
            consumer_content_install_itinerary, UNIT_INSTALL_ACTION, consumer_id, units,
            install_options, schedule_data)

    @staticmethod
    def update_unit_install_schedule(consumer_id, schedule_id, units=None, install_options=None,
                                     schedule_data=None):
        """
        Update an existing schedule for installing content units on a consumer.

        :param consumer_id:     unique id for the consumer
        :param schedule_id:     unique id for the schedule
        :param units: optional  list of units to install
        :param install_options: optional options to pass to the install manager
        :param schedule_data:   optional schedule updates
        """
        return ConsumerScheduleManager._update_schedule(consumer_id, schedule_id, units,
                                                        install_options, schedule_data)

    @staticmethod
    def delete_unit_install_schedule(consumer_id, schedule_id):
        """
        Delete an existing schedule for installing content units on a consumer.

        :param consumer_id: unique id of the consumer
        :param schedule_id: unique id of the schedule
        """
        return ConsumerScheduleManager._delete_schedule(consumer_id, schedule_id)

    def delete_all_unit_install_schedules(self, consumer_id):
        """
        Delete all unit install schedules for a consumer.
        Useful for unassociating consumers from the server.
        @param consumer_id: unique id of the consumer
        """
        return self._delete_all_schedules(UNIT_INSTALL_ACTION, consumer_id)


create_unit_install_schedule = task(
    ConsumerContentInstallScheduleManager.create_unit_install_schedule, base=Task)
delete_unit_install_schedule = task(
    ConsumerContentInstallScheduleManager.delete_unit_install_schedule, base=Task)
update_unit_install_schedule = task(
    ConsumerContentInstallScheduleManager.update_unit_install_schedule, base=Task)


class ConsumerContentUpdateScheduleManager(ConsumerScheduleManager):
    @staticmethod
    def create_unit_update_schedule(consumer_id, units, update_options, schedule_data):
        """
        Create a schedule for updating content units on a consumer.

        :param consumer_id:    unique id for the consumer
        :param units:          list of unit type and unit key dicts
        :param update_options: options to pass to the update manager
        :param schedule_data:  scheduling data
        :return:               schedule id
        """
        return ConsumerScheduleManager._create_schedule(
            consumer_content_update_itinerary, UNIT_UPDATE_ACTION, consumer_id, units,
            update_options, schedule_data)

    @staticmethod
    def update_unit_update_schedule(consumer_id, schedule_id, units=None, update_options=None,
                                    schedule_data=None):
        """
        Update an existing schedule for updating content units on a consumer.

        :param consumer_id:    unique id for the consumer
        :param schedule_id:    unique id for the schedule
        :param units:          optional list of units to update
        :param update_options: optional options to pass to the update manager
        :param schedule_data:  optional schedule updates
        """
        return ConsumerScheduleManager._update_schedule(consumer_id, schedule_id, units,
                                                        update_options, schedule_data)

    @staticmethod
    def delete_unit_update_schedule(consumer_id, schedule_id):
        """
        Delete an existing schedule for updating content units on a consumer.

        :param consumer_id: unique id of the consumer
        :param schedule_id: unique id of the schedule
        """
        return ConsumerScheduleManager._delete_schedule(consumer_id, schedule_id)

    def delete_all_unit_update_schedules(self, consumer_id):
        """
        Delete all unit update schedules for a consumer.
        Useful for unassociating consumers from the server.
        @param consumer_id: unique id of the consumer
        """
        return self._delete_all_schedules(UNIT_UPDATE_ACTION, consumer_id)


create_unit_update_schedule = task(
    ConsumerContentUpdateScheduleManager.create_unit_update_schedule, base=Task)
delete_unit_update_schedule = task(
    ConsumerContentUpdateScheduleManager.delete_unit_update_schedule, base=Task)
update_unit_update_schedule = task(
    ConsumerContentUpdateScheduleManager.update_unit_update_schedule, base=Task)


class ConsumerContentUninstallScheduleManager(ConsumerScheduleManager):
    @staticmethod
    def create_unit_uninstall_schedule(consumer_id, units, uninstall_options, schedule_data):
        """
        Create a schedule for uninstalling content units on a consumer.

        :param consumer_id:       unique id for the consumer
        :param units:             list of unit type and unit key dicts
        :param uninstall_options: options to pass to the uninstall manager
        :param schedule_data:     scheduling data
        :return:                  schedule id
        """
        return ConsumerScheduleManager._create_schedule(
            consumer_content_uninstall_itinerary, UNIT_UNINSTALL_ACTION, consumer_id, units,
            uninstall_options, schedule_data)

    @staticmethod
    def update_unit_uninstall_schedule(consumer_id, schedule_id, units=None,
                                       uninstall_options=None, schedule_data=None):
        """
        Update an existing schedule for uninstalling content units on a consumer.

        :param consumer_id:       unique id for the consumer
        :param schedule_id:       unique id for the schedule
        :param units:             optional list of units to uninstall
        :param uninstall_options: optional options to pass to the uninstall manager
        :param schedule_data:     optional schedule updates
        """
        return ConsumerScheduleManager._update_schedule(consumer_id, schedule_id, units,
                                                        uninstall_options, schedule_data)

    @staticmethod
    def delete_unit_uninstall_schedule(consumer_id, schedule_id):
        """
        Delete an existing schedule for uninstalling content units on a consumer.

        :param consumer_id: unique id of the consumer
        :param schedule_id: unique id of the schedule
        """
        return ConsumerScheduleManager._delete_schedule(consumer_id, schedule_id)

    def delete_all_unit_uninstall_schedules(self, consumer_id):
        """
        Delete all unit uninstall schedules for a consumer.
        Useful for unassociating consumers from the server.
        @param consumer_id: unique id of the consumer
        """
        return self._delete_all_schedules(UNIT_UNINSTALL_ACTION, consumer_id)


create_unit_uninstall_schedule = task(
    ConsumerContentUninstallScheduleManager.create_unit_uninstall_schedule, base=Task)
delete_unit_uninstall_schedule = task(
    ConsumerContentUninstallScheduleManager.delete_unit_uninstall_schedule, base=Task)
update_unit_uninstall_schedule = task(
    ConsumerContentUninstallScheduleManager.update_unit_uninstall_schedule, base=Task)
