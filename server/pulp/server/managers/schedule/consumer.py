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
from pulp.server.db.model.consumer import Consumer
from pulp.server.db.model.dispatch import ScheduledCall
from pulp.server.managers import factory as managers_factory
from pulp.server.managers.schedule import utils
from pulp.server.tasks import consumer


_UNIT_OPTION_KEYS = ('options',)

UNIT_INSTALL_ACTION = 'scheduled_unit_install'
UNIT_UPDATE_ACTION = 'scheduled_unit_update'
UNIT_UNINSTALL_ACTION = 'scheduled_unit_uninstall'

ACTIONS_TO_TASKS = {
    UNIT_INSTALL_ACTION: consumer.install_content,
    UNIT_UPDATE_ACTION: consumer.update_content,
    UNIT_UNINSTALL_ACTION: consumer.uninstall_content,
}


class ConsumerScheduleManager(object):
    """
    Abstract base class for consumer content management schedules.
    """
    @staticmethod
    def _validate_consumer(consumer_id):
        consumer_manager = managers_factory.consumer_manager()
        consumer_manager.get_consumer(consumer_id)

    @staticmethod
    def get(consumer_id, action=None):
        results = utils.get_by_resource(Consumer.build_resource_tag(consumer_id))
        if action:
            task = ACTIONS_TO_TASKS[action]
            return filter(lambda schedule: schedule.task == task.name, results)
        else:
            return results

    @classmethod
    def create_schedule(cls, action_name, consumer_id, units, options,
                         schedule_data):
        """

        :param action_name:
        :param consumer_id:
        :param units:
        :param options:
        :param schedule_data:
        :return:
        :rtype:     pulp.server.db.models.dispatch.ScheduledCall
        """
        cls._validate_consumer(consumer_id)
        utils.validate_keys(options, _UNIT_OPTION_KEYS)
        if 'schedule' not in schedule_data:
            raise exceptions.MissingValue(['schedule'])
        utils.validate_initial_schedule_options(schedule_data)

        task = ACTIONS_TO_TASKS[action_name]
        args = [consumer_id]
        kwargs = {'units': units,
                  'options': options.get('options', {})}
        resource = Consumer.build_resource_tag(consumer_id)

        schedule = ScheduledCall(schedule_data['schedule'], task, args=args,
                                 kwargs=kwargs, resource=resource)
        schedule.save()
        return schedule

    @staticmethod
    def update_schedule(consumer_id, schedule_id, units=None, options=None,
                         schedule_data=None):
        """

        :param consumer_id:
        :param schedule_id:
        :param units:
        :param options:
        :param schedule_data:
        :return:
        :rtype:     pulp.server.db.models.dispatch.ScheduledCall
        """
        ConsumerScheduleManager._validate_consumer(consumer_id)
        schedule_updates = copy.copy(schedule_data) or {}

        if units is not None:
            schedule_updates.setdefault('kwargs', {})['units'] = units
        if options is not None:
            schedule_updates.setdefault('kwargs', {})['options'] = options

        return utils.update(schedule_id, schedule_updates)

    @staticmethod
    def delete_schedule(consumer_id, schedule_id):
        ConsumerScheduleManager._validate_consumer(consumer_id)

        utils.delete(schedule_id)
