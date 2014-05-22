# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from datetime import datetime
from pymongo.errors import DuplicateKeyError

from pulp.common import constants, dateutils
from pulp.server.db.model.dispatch import TaskStatus
from pulp.server.exceptions import DuplicateResource, InvalidValue, MissingResource


class TaskStatusManager(object):
    """
    Performs task status related functions including both CRUD operations and queries on task
    statuses. Task statuses returned by query calls are TaskStatus SON objects from the database.
    """

    @staticmethod
    def create_task_status(task_id, queue, tags=None, state=None):
        """
        Creates a new task status for given task_id.

        :param task_id:           identity of the task this status corresponds to
        :type  task_id:           basestring
        :param queue:             The name of the queue that the Task is in
        :type  queue:             basestring
        :param tags:              custom tags on the task
        :type  tags:              list of basestrings or None
        :param state:             state of callable in its lifecycle
        :type  state:             basestring
        :return:                  task status document
        :rtype:                   dict
        :raise DuplicateResource: if there is already a task status entry with the requested task id
        :raise InvalidValue:      if any of the fields are unacceptable
        """
        invalid_values = []
        if task_id is None:
            invalid_values.append('task_id')
        if queue is None:
            invalid_values.append('queue')
        if tags is not None and not isinstance(tags, list):
            invalid_values.append('tags')
        if state is not None and not isinstance(state, basestring):
            invalid_values.append('state')
        if invalid_values:
            raise InvalidValue(invalid_values)

        if not state:
            state = constants.CALL_WAITING_STATE

        task_status = TaskStatus(task_id=task_id, queue=queue, tags=tags, state=state)
        try:
            TaskStatus.get_collection().save(task_status, safe=True)
        except DuplicateKeyError:
            raise DuplicateResource(task_id)

        created = TaskStatus.get_collection().find_one({'task_id': task_id})
        return created

    @staticmethod
    def set_task_accepted(task_id):
        """
        Update a task's state to reflect that it has been accepted.
        :param task_id: The identity of the task to be updated.
        :type  task_id: basestring
        """
        delta = {
            'state': constants.CALL_ACCEPTED_STATE
        }
        TaskStatusManager.update_task_status(task_id=task_id, delta=delta)

    @staticmethod
    def set_task_started(task_id):
        """
        Update a task's state to reflect that it has started running.
        :param task_id: The identity of the task to be updated.
        :type  task_id: basestring
        """
        now = datetime.now(dateutils.utc_tz())
        start_time = dateutils.format_iso8601_datetime(now)
        delta = {
            'state': constants.CALL_RUNNING_STATE,
            'start_time': start_time,
        }
        TaskStatusManager.update_task_status(task_id=task_id, delta=delta)

    @staticmethod
    def set_task_succeeded(task_id, result=None):
        """
        Update a task's state to reflect that it succeeded.
        :param task_id: The identity of the task to be updated.
        :type  task_id: basestring
        :param result: The optional value returned by the task execution.
        :type result: anything
        """
        now = datetime.now(dateutils.utc_tz())
        finish_time = dateutils.format_iso8601_datetime(now)
        delta = {
            'state': constants.CALL_FINISHED_STATE,
            'finish_time': finish_time,
            'result': result
        }
        TaskStatusManager.update_task_status(task_id=task_id, delta=delta)

    @staticmethod
    def set_task_failed(task_id, traceback=None):
        """
        Update a task's state to reflect that it succeeded.
        :param task_id: The identity of the task to be updated.
        :type  task_id: basestring
        :ivar traceback: A string representation of the traceback resulting from the task execution.
        :type traceback: basestring
        """
        now = datetime.now(dateutils.utc_tz())
        finish_time = dateutils.format_iso8601_datetime(now)
        delta = {
            'state': constants.CALL_ERROR_STATE,
            'finish_time': finish_time,
            'traceback': traceback
        }
        TaskStatusManager.update_task_status(task_id=task_id, delta=delta)

    @staticmethod
    def update_task_status(task_id, delta):
        """
        Updates status of the task with given task id. Only the following
        fields may be updated through this call:
        * state
        * result
        * traceback
        * start_time
        * finish_time
        * error
        * spawned_tasks
        * progress_report
        Other fields found in delta will be ignored.

        :param task_id: identity of the task this status corresponds to
        :type  task_id: basetring
        :param delta: list of attributes and their new values to change
        :type  delta: dict
        :return: updated serialized task status
        :rtype:  dict
        :raise MissingResource: if there is no task status corresponding to the given task_id
        """

        task_status = TaskStatus.get_collection().find_one({'task_id': task_id})
        if task_status is None:
            raise MissingResource(task_id)

        updatable_attributes = ['state', 'result', 'traceback', 'start_time', 'finish_time',
                                'error', 'spawned_tasks', 'progress_report']
        for key, value in delta.items():
            if key in updatable_attributes:
                task_status[key] = value

        TaskStatus.get_collection().save(task_status, safe=True)
        return task_status

    @staticmethod
    def delete_task_status(task_id):
        """
        Deletes the task status with given task id.

        :param task_id: identity of the task this status corresponds to
        :type  task_id: basestring
        :raise MissingResource: if the given task status does not exist
        :raise InvalidValue: if task_id is invalid
        """
        task_status = TaskStatus.get_collection().find_one({'task_id': task_id})
        if task_status is None:
            raise MissingResource(task_id)

        TaskStatus.get_collection().remove({'task_id': task_id}, safe=True)

    @staticmethod
    def find_all():
        """
        Returns serialized versions of all task statuses in the database.

        :return: pymongo cursor for the list of serialized task statuses
        :rtype:  pymongo.cursor.Cursor
        """
        all_task_statuses = TaskStatus.get_collection().find()
        return all_task_statuses

    @staticmethod
    def find_by_task_id(task_id):
        """
        Returns a serialized version the status of given task, if it exists.
        If a task status cannot be found with the given task_id, None is returned.

        :return: serialized task status
        :rtype:  dict or None
        """
        task_status = TaskStatus.get_collection().find_one({'task_id': task_id})
        return task_status

    @staticmethod
    def find_by_criteria(criteria):
        """
        Return a list of task statuses that match the provided criteria.

        :param criteria:    A Criteria object representing a search you want
                            to perform
        :type  criteria:    pulp.server.db.model.criteria.Criteria
        :return:    pymongo cursor for the TaskStatus instances satisfying the query
        :rtype:     pymongo.cursor.Cursor
        """
        return TaskStatus.get_collection().query(criteria)
