# -*- coding: utf-8 -*-
#
# Copyright © 2012-2014 Red Hat, Inc.
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
import itertools

from pulp.server.db.model.consumer import Consumer
from pulp.server.db.model.dispatch import ScheduledCall
from pulp.server.exceptions import MissingResource
from pulp.server.managers import factory as managers_factory
from pulp.server.managers.schedule import utils
from pulp.server.tasks import consumer


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
        """
        Determines if a given consumer_id is valid by checking its existence
        in the database.

        :param consumer_id: a unique ID for a consumer
        :type  consumer_id: basestring

        :raises:    pulp.server.exceptions.MissingResource
        """
        consumer_manager = managers_factory.consumer_manager()
        consumer_manager.get_consumer(consumer_id)

    @staticmethod
    def get(consumer_id, action=None):
        """
        Get a collection of schedules for the given consumer and action. If no
        action is specified, then all actions will be included.

        :param consumer_id: a unique ID for a consumer
        :type  consumer_id: basestring
        :param action:      a unique identifier for an action, one of
                            UNIT_INSTALL_ACTION, UNIT_UPDATE_ACTION,
                            UNIT_UNINSTALL_ACTION
        :type  action:      basestring

        :return:    iterator of ScheduledCall instances
        :rtype:     iterator
        """
        results = utils.get_by_resource(Consumer.build_resource_tag(consumer_id))
        if action:
            task = ACTIONS_TO_TASKS[action]
            return itertools.ifilter(lambda schedule: schedule.task == task.name, results)
        else:
            return results

    @classmethod
    def create_schedule(cls, action, consumer_id, units, options,
                        schedule, failure_threshold=None, enabled=True):
        """
        Creates a new schedule for a consumer action

        :param action:          a unique identified for an action, one of
                                UNIT_INSTALL_ACTION, UNIT_UPDATE_ACTION,
                                UNIT_UNINSTALL_ACTION
        :type  action:          basestring
        :param consumer_id:     a unique ID for a consumer
        :type  consumer_id:     basestring
        :param units:           A list of content units to be installed, each as
                                a dict in the form:
                                    { type_id:<str>, unit_key:<dict> }
        :type  units:           list
        :param options:         a dictionary that will be passed to the
                                action-appropriate task as the "options"
                                argument
        :type  options:         dict
        :param schedule:        ISO8601 string representation of the schedule
        :type  schedule:        basestring
        :param failure_threshold:   optional positive integer indicating how
                                many times this schedule's execution can fail
                                before being automatically disabled.
        :type  failure_threshold:   int or NoneType
        :param enabled:         boolean indicating if this schedule should
                                be actively loaded and executed by the
                                scheduler. Defaults to True.
        :type  enabled:         bool
        :return:    instance of the new ScheduledCal
        :rtype:     pulp.server.db.models.dispatch.ScheduledCall

        :raise:     pulp.server.exceptions.MissingResource
        """
        cls._validate_consumer(consumer_id)
        utils.validate_initial_schedule_options(schedule, failure_threshold, enabled)
        if not units:
            raise MissingResource(['units'])

        task = ACTIONS_TO_TASKS[action]
        args = [consumer_id]
        kwargs = {'units': units, 'options': options}
        resource = Consumer.build_resource_tag(consumer_id)

        schedule = ScheduledCall(schedule, task, args=args, kwargs=kwargs,
                                 resource=resource, failure_threshold=failure_threshold,
                                 enabled=enabled)
        schedule.save()
        return schedule

    @staticmethod
    def update_schedule(consumer_id, schedule_id, units=None, options=None,
                        schedule_data=None):
        """

        :param consumer_id:     a unique ID for a consumer
        :type  consumer_id:     basestring
        :param schedule_id:     a unique ID for the schedule being updated
        :type  schedule_id:     basestring
        :param units:           A list of content units to be installed, each as
                                a dict in the form:
                                    { type_id:<str>, unit_key:<dict> }
        :type  units:           list
        :param options:         a dictionary that will be passed to the
                                action-appropriate task as the "options"
                                argument
        :type  options:         dict
        :param schedule_data:   dictionary of keys and values that should be
                                applied as updates to the schedule. Keys must
                                be in ScheduledCall.USER_UPDATE_FIELDS

        :return:    instance of ScheduledCall representing the post-update state
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
        """
        Permanently deletes the schedule specified

        :param consumer_id:     a unique ID for a consumer
        :type  consumer_id:     basestring
        :param schedule_id:     a unique ID for the schedule being updated
        :type  schedule_id:     basestring
        """
        ConsumerScheduleManager._validate_consumer(consumer_id)

        utils.delete(schedule_id)
