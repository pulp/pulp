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
    def set_task_accepted(task_id):
        """
        Update a task's state to reflect that it has been accepted.
        :param task_id: The identity of the task to be updated.
        :type  task_id: basestring
        """
        TaskStatus.objects(task_id=task_id, state=constants.CALL_WAITING_STATE).\
            update_one(set__state=constants.CALL_ACCEPTED_STATE)

    @staticmethod
    def set_task_started(task_id, timestamp=None):
        """
        Update a task's state to reflect that it has started running.
        :param task_id: The identity of the task to be updated.
        :type  task_id: basestring
        :param timestamp: The (optional) ISO-8601 finished timestamp (UTC).
        :type timestamp: str
        """
        if not timestamp:
            now = datetime.now(dateutils.utc_tz())
            started = dateutils.format_iso8601_datetime(now)
        else:
            started = timestamp

        TaskStatus.objects(task_id=task_id).update_one(set__start_time=started)

        TaskStatus.objects(task_id=task_id,
                           state__in=[constants.CALL_WAITING_STATE, constants.CALL_ACCEPTED_STATE]).\
            update_one(set__state=constants.CALL_RUNNING_STATE)

    @staticmethod
    def set_task_succeeded(task_id, result=None, timestamp=None):
        """
        Update a task's state to reflect that it has succeeded.
        :param task_id: The identity of the task to be updated.
        :type  task_id: basestring
        :param result: The optional value returned by the task execution.
        :type result: anything
        :param timestamp: The (optional) ISO-8601 finished timestamp (UTC).
        :type timestamp: str
        """
        if not timestamp:
            now = datetime.now(dateutils.utc_tz())
            finished = dateutils.format_iso8601_datetime(now)
        else:
            finished = timestamp

        TaskStatus.objects(task_id=task_id).update_one(set__finish_time=finished,
                                                       set__state=constants.CALL_FINISHED_STATE,
                                                       set__result=result)

    @staticmethod
    def set_task_failed(task_id, traceback=None, timestamp=None):
        """
        Update a task's state to reflect that it has succeeded.
        :param task_id: The identity of the task to be updated.
        :type  task_id: basestring
        :ivar traceback: A string representation of the traceback resulting from the task execution.
        :type traceback: basestring
        :param timestamp: The (optional) ISO-8601 finished timestamp (UTC).
        :type timestamp: str
        """
        if not timestamp:
            now = datetime.now(dateutils.utc_tz())
            finished = dateutils.format_iso8601_datetime(now)
        else:
            finished = timestamp

        TaskStatus.objects(task_id=task_id).update_one(set__finish_time=finished,
                                                       set__state=constants.CALL_ERROR_STATE,
                                                       set__traceback=traceback)

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
        :return:    pymongo cursor for the TaskStatus instances satisfying the query
        :rtype:     pymongo.cursor.Cursor
        """
        return TaskStatus.get_collection().query(criteria)
