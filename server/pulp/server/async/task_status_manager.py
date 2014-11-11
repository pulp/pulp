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
    def create_task_status(task_id, worker_name=None, tags=None, state=None):
        """
        Creates a new task status for given task_id.

        :param task_id:           identity of the task this status corresponds to
        :type  task_id:           basestring
        :param worker_name:       The name of the worker that the Task is in
        :type  worker_name:       basestring
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
        if worker_name is not None and not isinstance(worker_name, basestring):
            invalid_values.append('worker_name')
        if tags is not None and not isinstance(tags, list):
            invalid_values.append('tags')
        if state is not None and not isinstance(state, basestring):
            invalid_values.append('state')
        if invalid_values:
            raise InvalidValue(invalid_values)

        if not state:
            state = constants.CALL_WAITING_STATE

        task_status = TaskStatus(task_id=task_id, worker_name=worker_name, tags=tags, state=state)
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
        collection = TaskStatus.get_collection()

        select = {
            'task_id': task_id,
            'state': constants.CALL_WAITING_STATE
        }
        update = {
            '$set': {'state': constants.CALL_ACCEPTED_STATE}
        }

        collection.update(select, update, safe=True)

    @staticmethod
    def set_task_started(task_id, timestamp=None):
        """
        Update a task's state to reflect that it has started running.
        :param task_id: The identity of the task to be updated.
        :type  task_id: basestring
        :param timestamp: The (optional) ISO-8601 finished timestamp (UTC).
        :type timestamp: str
        """
        collection = TaskStatus.get_collection()

        if not timestamp:
            now = datetime.now(dateutils.utc_tz())
            started = dateutils.format_iso8601_datetime(now)
        else:
            started = timestamp

        select = {
            'task_id': task_id
        }
        update = {
            '$set': {'start_time': started}
        }

        collection.update(select, update, safe=True)

        select = {
            'task_id': task_id,
            'state': {'$in': [constants.CALL_WAITING_STATE, constants.CALL_ACCEPTED_STATE]}
        }
        update = {
            '$set': {'state': constants.CALL_RUNNING_STATE}
        }

        collection.update(select, update, safe=True)

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
        collection = TaskStatus.get_collection()

        if not timestamp:
            now = datetime.now(dateutils.utc_tz())
            finished = dateutils.format_iso8601_datetime(now)
        else:
            finished = timestamp

        update = {
            '$set': {
                'finish_time': finished,
                'state': constants.CALL_FINISHED_STATE,
                'result': result
            }
        }

        collection.update({'task_id': task_id}, update, safe=True)

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
        collection = TaskStatus.get_collection()

        if not timestamp:
            now = datetime.now(dateutils.utc_tz())
            finished = dateutils.format_iso8601_datetime(now)
        else:
            finished = timestamp

        update = {
            '$set': {
                'finish_time': finished,
                'state': constants.CALL_ERROR_STATE,
                'traceback': traceback
            }
        }

        collection.update({'task_id': task_id}, update, safe=True)

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
