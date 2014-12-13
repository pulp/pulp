from datetime import datetime
from mongoengine import NotUniqueError, ValidationError

from pulp.common import constants, dateutils
from pulp.server.db.model.dispatch import TaskStatus
from pulp.server.exceptions import DuplicateResource, InvalidValue, MissingResource


class TaskStatusManager(object):
    """
    Performs task status related functions including both CRUD operations and queries on task
    statuses. Task statuses returned by query calls are TaskStatus SON objects from the database.
    """

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

        task_status = TaskStatus.objects(task_id=task_id).first()
        if task_status is None:
            raise MissingResource(task_id)

        updatable_attributes = ['state', 'result', 'traceback', 'start_time', 'finish_time',
                                'error', 'spawned_tasks', 'progress_report']
        for key, value in delta.items():
            if key in updatable_attributes:
                task_status[key] = value

        task_status.save()
        updated = TaskStatus.objects(task_id=task_id).first()
        updated = updated.as_dict() if updated else None
        return updated

    @staticmethod
    def find_by_criteria(criteria):
        """
        Return a list of task statuses that match the provided criteria.

        :param criteria:    A Criteria object representing a search you want
                            to perform
        :type  criteria:    pulp.server.db.model.criteria.Criteria
        :return:    mongoengine queryset object
        :rtype:     mongoengine.queryset.QuerySet
        """
        return TaskStatus.objects.find_by_criteria(criteria)
