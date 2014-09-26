from datetime import datetime
from gettext import gettext as _
import logging
import signal
import time
import uuid

from celery import task, Task as CeleryTask, current_task
from celery.app import control, defaults
from celery.result import AsyncResult
from celery.signals import worker_init

from pulp.common import constants, dateutils
from pulp.server.async.celery_instance import celery, RESOURCE_MANAGER_QUEUE, \
    DEDICATED_QUEUE_EXCHANGE
from pulp.server.async.task_status_manager import TaskStatusManager
from pulp.server.exceptions import PulpException, MissingResource
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.dispatch import TaskStatus
from pulp.server.db.model.resources import ReservedResource, Worker
from pulp.server.exceptions import NoWorkers
from pulp.server.managers import resources


controller = control.Control(app=celery)
logger = logging.getLogger(__name__)


@task(acks_late=True)
def _queue_reserved_task(name, task_id, resource_id, inner_args, inner_kwargs):
    """
    A task that encapsulates another task to be dispatched later. This task being encapsulated is
    called the "inner" task, and a task name, UUID, and accepts a list of positional args
    and keyword args for the inner task. These arguments are named inner_args and inner_kwargs.
    inner_args is a list, and inner_kwargs is a dictionary passed to the inner task as positional
    and keyword arguments using the * and ** operators.

    The inner task is dispatched into a dedicated queue for a worker that is decided at dispatch
    time. The logic deciding which queue receives a task is controlled through the
    find_worker function.

    :param name:          The name of the task to be called
    :type name:           basestring
    :param inner_task_id: The UUID to be set on the task being called. By providing
                          the UUID, the caller can have an asynchronous reference to the inner task
                          that will be dispatched.
    :type inner_task_id:  basestring
    :param resource_id:   The name of the resource you wish to reserve for your task. The system
                          will ensure that no other tasks that want that same reservation will run
                          concurrently with yours.
    :type  resource_id:   basestring

    :return: None
    """
    while True:
        try:
            worker = resources.get_worker_for_reservation(resource_id)
        except NoWorkers:
            pass
        else:
            break

        try:
            worker = resources.get_unreserved_worker()
        except NoWorkers:
            pass
        else:
            break

        # No worker is ready for this work, so we need to wait
        time.sleep(0.25)

    ReservedResource(task_id, worker['name'], resource_id).save()

    inner_kwargs['routing_key'] = worker.name
    inner_kwargs['exchange'] = DEDICATED_QUEUE_EXCHANGE
    inner_kwargs['task_id'] = task_id

    try:
        celery.tasks[name].apply_async(*inner_args, **inner_kwargs)
    finally:
        _release_resource.apply_async((task_id, ), routing_key=worker.name,
                                      exchange=DEDICATED_QUEUE_EXCHANGE)


def _delete_worker(name, normal_shutdown=False):
    """
    Delete the Worker with _id name from the database, cancel any associated tasks and reservations

    If the worker shutdown normally, no message is logged, otherwise an error level message is
    logged. Default is to assume the worker did not shut down normally.

    Any resource reservations associated with this worker are cleaned up by this function.

    Any tasks associated with this worker are explicitly canceled.

    :param name:            The name of the worker you wish to delete. In the database, the _id
                            field is the name.
    :type  name:            basestring
    :param normal_shutdown: True if the worker shutdown normally, False otherwise.  Defaults to
                            False.
    :type normal_shutdown:  bool
    """
    if normal_shutdown is False:
        msg = _('The worker named %(name)s is missing. Canceling the tasks in its queue.')
        msg = msg % {'name': name}
        logger.error(msg)

    # Delete the worker document
    worker_list = list(resources.filter_workers(Criteria(filters={'_id': name})))
    if len(worker_list) > 0:
        worker_document = worker_list[0]
        worker_document.delete()

    # Delete all reserved_resource documents for the worker
    ReservedResource.get_collection().remove({'worker_name': name})

    # Cancel all of the tasks that were assigned to this worker's queue
    worker = Worker.from_bson({'_id': name})
    for task in TaskStatusManager.find_by_criteria(
            Criteria(
                filters={'worker_name': worker.name,
                         'state': {'$in': constants.CALL_INCOMPLETE_STATES}})):
        cancel(task['task_id'])


@task
def _release_resource(task_id):
    """
    Do not queue this task yourself. It will be used automatically when your task is dispatched by
    the _queue_reserved_task task.

    When a resource-reserving task is complete, this method releases the resource by removing the
    ReservedResource object by UUID.

    :param task_id: The UUID of the task that requested the reservation
    :type  task_id: basestring
    """
    ReservedResource.get_collection().remove({'_id': task_id})


class TaskResult(object):
    """
    The TaskResult object is used for returning errors and spawned tasks that do not affect the
    primary status of the task.

    Errors that don't affect the current task status might be related to secondary actions
    where the primary action of the async-task was successful

    Spawned tasks are items such as the individual tasks for updating the bindings on
    each consumer when a repo distributor is updated.
    """

    def __init__(self, result=None, error=None, spawned_tasks=None):
        """
        :param result: The return value from the task
        :type result: dict
        :param error: The PulpException for the error & sub-errors that occured
        :type error: pulp.server.exception.PulpException
        :param spawned_tasks: A list of task status objects for tasks that were created by this
                              task and are tracked through the pulp database.
                              Alternately an AsyncResult, or the task_id of the task created.
        :type spawned_tasks: list of TaskStatus, AsyncResult, or str objects
        """
        self.return_value = result
        self.error = error
        self.spawned_tasks = []
        if spawned_tasks:
            for spawned_task in spawned_tasks:
                if isinstance(spawned_task, dict):
                    self.spawned_tasks.append({'task_id': spawned_task.get('task_id')})
                elif isinstance(spawned_task, AsyncResult):
                    self.spawned_tasks.append({'task_id': spawned_task.id})
                else:  # This should be a string
                    self.spawned_tasks.append({'task_id': spawned_task})

    @classmethod
    def from_async_result(cls, async_result):
        """
        Create a TaskResult object from a celery async_result type

        :param async_result: The result object to use as a base
        :type async_result: celery.result.AsyncResult
        :returns: a TaskResult containing the async task in it's spawned_tasks list
        :rtype: TaskResult
        """
        return cls(spawned_tasks=[{'task_id': async_result.id}])

    @classmethod
    def from_task_status_dict(cls, task_status):
        """
        Create a TaskResult object from a celery async_result type

        :param task_status: The dictionary representation of a TaskStatus
        :type task_status: dict
        :returns: a TaskResult containing the task in it's spawned_tasks lsit
        :rtype: TaskResult
        """
        return cls(spawned_tasks=[{'task_id': task_status.get('task_id')}])

    def serialize(self):
        """
        Serialize the output to a dictionary
        """
        serialized_error = self.error
        if serialized_error:
            serialized_error = self.error.to_dict()
        data = {
            'result': self.return_value,
            'error': serialized_error,
            'spawned_tasks': self.spawned_tasks}
        return data


class ReservedTaskMixin(object):
    def apply_async_with_reservation(self, resource_type, resource_id, *args, **kwargs):
        """
        This method allows the caller to schedule the ReservedTask to run asynchronously just like
        Celery's apply_async(), while also making the named resource. No two tasks that claim the
        same resource reservation can execute concurrently. It accepts type and id of a resource
        and combines them to form a resource id.

        This does not dispatch the task directly, but instead promises to dispatch it later by
        encapsulating the desired task through a call to a _queue_reserved_task task. See the
        docblock on _queue_reserved_task for more information on this.

        This method creates a TaskStatus as a placeholder for later updates. Pulp expects to poll
        on a task just after calling this method, so a TaskStatus entry needs to exist for it
        before it returns.

        For a list of parameters accepted by the *args and **kwargs parameters, please see the
        docblock for the apply_async() method.

        :param resource_type: A string that identifies type of a resource
        :type resource_type:  basestring
        :param resource_id:   A string that identifies some named resource, guaranteeing that only
                              one task reserving this same string can happen at a time.
        :type  resource_id:   basestring
        :param tags:          A list of tags (strings) to place onto the task, used for searching
                              for tasks by tag
        :type  tags:          list
        :return:              An AsyncResult instance as returned by Celery's apply_async
        :rtype:               celery.result.AsyncResult
        """
        # Form a resource_id for reservation by combining given resource type and id. This way,
        # two different resources having the same id will not block each other.
        resource_id = ":".join((resource_type, resource_id))
        inner_task_id = str(uuid.uuid4())
        task_name = self.name
        tags = kwargs.get('tags', [])

        # Create a new task status with the task id and tags.
        task_status = TaskStatus(task_id=inner_task_id, task_type=task_name,
                                 state=constants.CALL_WAITING_STATE, tags=tags)
        # To avoid the race condition where __call__ method below is called before
        # this change is propagated to all db nodes, using an 'upsert' here and setting
        # the task state to 'waiting' only on an insert.
        task_status.save(fields_to_set_on_insert=['state', 'start_time'])

        _queue_reserved_task.apply_async(args=[task_name, inner_task_id, resource_id, args, kwargs],
                                         queue=RESOURCE_MANAGER_QUEUE)
        return AsyncResult(inner_task_id)


class Task(CeleryTask, ReservedTaskMixin):
    """
    This is a custom Pulp subclass of the Celery Task object. It allows us to inject some custom
    behavior into each Pulp task, including management of resource locking.
    """
    def apply_async(self, *args, **kwargs):
        """
        A wrapper around the Celery apply_async method. It allows us to accept a few more
        parameters than Celery does for our own purposes, listed below. It also allows us
        to create and update task status which can be used to track status of this task
        during it's lifetime.

        :param queue:       The queue that the task has been placed into (optional, defaults to
                            the general Celery queue.)
        :type  queue:       basestring
        :param tags:        A list of tags (strings) to place onto the task, used for searching for
                            tasks by tag
        :type  tags:        list
        :return:            An AsyncResult instance as returned by Celery's apply_async
        :rtype:             celery.result.AsyncResult
        """
        routing_key = kwargs.get('routing_key',
                                 defaults.NAMESPACES['CELERY']['DEFAULT_ROUTING_KEY'].default)
        tags = kwargs.pop('tags', [])

        async_result = super(Task, self).apply_async(*args, **kwargs)
        async_result.tags = tags

        # Create a new task status with the task id and tags.
        task_status = TaskStatus(
            task_id=async_result.id, task_type=self.name,
            state=constants.CALL_WAITING_STATE, worker_name=routing_key, tags=tags)
        # To avoid the race condition where __call__ method below is called before
        # this change is propagated to all db nodes, using an 'upsert' here and setting
        # the task state to 'waiting' only on an insert.
        task_status.save(fields_to_set_on_insert=['state', 'start_time'])
        return async_result

    def __call__(self, *args, **kwargs):
        """
        This overrides CeleryTask's __call__() method. We use this method
        for task state tracking of Pulp tasks.
        """
        # Check task status and skip running the task if task state is 'canceled'.
        task_status = TaskStatusManager.find_by_task_id(task_id=self.request.id)
        if task_status and task_status['state'] == constants.CALL_CANCELED_STATE:
            logger.debug("Task cancel received for task-id : [%s]" % self.request.id)
            return
        # Update start_time and set the task state to 'running' for asynchronous tasks.
        # Skip updating status for eagerly executed tasks, since we don't want to track
        # synchronous tasks in our database.
        if not self.request.called_directly:
            now = datetime.now(dateutils.utc_tz())
            start_time = dateutils.format_iso8601_datetime(now)
            # Using 'upsert' to avoid a possible race condition described in the apply_async method
            # above.
            TaskStatus.get_collection().update(
                {'task_id': self.request.id},
                {'$set': {'state': constants.CALL_RUNNING_STATE,
                          'start_time': start_time}},
                upsert=True)
        # Run the actual task
        logger.debug("Running task : [%s]" % self.request.id)
        return super(Task, self).__call__(*args, **kwargs)

    def on_success(self, retval, task_id, args, kwargs):
        """
        This overrides the success handler run by the worker when the task
        executes successfully. It updates state, finish_time and traceback
        of the relevant task status for asynchronous tasks. Skip updating status
        for synchronous tasks.

        :param retval:  The return value of the task.
        :param task_id: Unique id of the executed task.
        :param args:    Original arguments for the executed task.
        :param kwargs:  Original keyword arguments for the executed task.
        """
        logger.debug("Task successful : [%s]" % task_id)
        if not self.request.called_directly:
            now = datetime.now(dateutils.utc_tz())
            finish_time = dateutils.format_iso8601_datetime(now)
            delta = {'finish_time': finish_time,
                     'result': retval}
            task_status = TaskStatusManager.find_by_task_id(task_id)
            # Only set the state to finished if it's not already in a complete state. This is
            # important for when the task has been canceled, so we don't move the task from canceled
            # to finished.
            if task_status['state'] not in constants.CALL_COMPLETE_STATES:
                delta['state'] = constants.CALL_FINISHED_STATE
            if isinstance(retval, TaskResult):
                delta['result'] = retval.return_value
                if retval.error:
                    delta['error'] = retval.error.to_dict()
                if retval.spawned_tasks:
                    task_list = []
                    for spawned_task in retval.spawned_tasks:
                        if isinstance(spawned_task, AsyncResult):
                            task_list.append(spawned_task.task_id)
                        elif isinstance(spawned_task, dict):
                            task_list.append(spawned_task['task_id'])
                    delta['spawned_tasks'] = task_list
            if isinstance(retval, AsyncResult):
                delta['spawned_tasks'] = [retval.task_id, ]
                delta['result'] = None

            TaskStatusManager.update_task_status(task_id=task_id, delta=delta)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        This overrides the error handler run by the worker when the task fails.
        It updates state, finish_time and traceback of the relevant task status
        for asynchronous tasks. Skip updating status for synchronous tasks.

        :param exc:     The exception raised by the task.
        :param task_id: Unique id of the failed task.
        :param args:    Original arguments for the executed task.
        :param kwargs:  Original keyword arguments for the executed task.
        :param einfo:   celery's ExceptionInfo instance, containing serialized traceback.
        """
        logger.debug("Task failed : [%s]" % task_id)
        if not self.request.called_directly:
            now = datetime.now(dateutils.utc_tz())
            finish_time = dateutils.format_iso8601_datetime(now)
            delta = {'state': constants.CALL_ERROR_STATE,
                     'finish_time': finish_time,
                     'traceback': einfo.traceback}
            if not isinstance(exc, PulpException):
                exc = PulpException(str(exc))
            delta['error'] = exc.to_dict()

            TaskStatusManager.update_task_status(task_id=task_id, delta=delta)


def cancel(task_id):
    """
    Cancel the task that is represented by the given task_id. This method cancels only the task
    with given task_id, not the spawned tasks. This also updates task's state to 'canceled'.

    :param task_id: The ID of the task you wish to cancel
    :type  task_id: basestring

    :raises MissingResource: if a task with given task_id does not exist
    :raises PulpCodedException: if given task is already in a complete state
    """
    task_status = TaskStatusManager.find_by_task_id(task_id)
    if task_status is None:
        raise MissingResource(task_id)
    if task_status['state'] in constants.CALL_COMPLETE_STATES:
        # If the task is already done, just stop
        msg = _('Task [%(task_id)s] already in a completed state: %(state)s')
        logger.info(msg % {'task_id': task_id, 'state': task_status['state']})
        return
    controller.revoke(task_id, terminate=True)
    TaskStatus.get_collection().find_and_modify(
        {'task_id': task_id, 'state': {'$nin': constants.CALL_COMPLETE_STATES}},
        {'$set': {'state': constants.CALL_CANCELED_STATE}})
    msg = _('Task canceled: %(task_id)s.')
    msg = msg % {'task_id': task_id}
    logger.info(msg)


def get_current_task_id():
    """"
    Get the current task id from celery. If this is called outside of a running
    celery task it will return None

    :return: The ID of the currently running celery task or None if not in a task
    :rtype: str
    """
    if current_task and current_task.request and current_task.request.id:
        return current_task.request.id
    return None


def register_sigterm_handler(f, handler):
    """
    register_signal_handler is a method or function decorator. It will register a special signal
    handler for SIGTERM that will call handler() with no arguments if SIGTERM is received during the
    operation of f. Once f has completed, the signal handler will be restored to the handler that
    was in place before the method began.

    :param f:       The method or function that should be wrapped.
    :type  f:       instancemethod or function
    :param handler: The method or function that should be called when we receive SIGTERM.
                    handler will be called with no arguments.
    :type  handler: instancemethod or function
    :return:        A wrapped version of f that performs the signal registering and unregistering.
    :rtype:         instancemethod or function
    """
    def sigterm_handler(signal_number, stack_frame):
        """
        This is the signal handler that gets installed to handle SIGTERM. We don't wish to pass the
        signal_number or the stack_frame on to handler, so its only purpose is to avoid
        passing these arguments onward. It calls handler().

        :param signal_number: The signal that is being handled. Since we have registered for
                              SIGTERM, this will be signal.SIGTERM.
        :type  signal_number: int
        :param stack_frame:   The current execution stack frame
        :type  stack_frame:   None or frame
        """
        handler()

    def wrap_f(*args, **kwargs):
        """
        This function is a wrapper around f. It replaces the signal handler for SIGTERM with
        signerm_handler(), calls f, sets the SIGTERM handler back to what it was before, and then
        returns the return value from f.

        :param args:   The positional arguments to be passed to f
        :type  args:   tuple
        :param kwargs: The keyword arguments to be passed to f
        :type  kwargs: dict
        :return:       The return value from calling f
        :rtype:        Could be anything!
        """
        old_signal = signal.signal(signal.SIGTERM, sigterm_handler)
        try:
            return f(*args, **kwargs)
        finally:
            signal.signal(signal.SIGTERM, old_signal)

    return wrap_f


@worker_init.connect
def cleanup_old_worker(*args, **kwargs):
    """
    Cleans up old state if this worker was previously running, but died unexpectedly.

    In those cases, any Pulp tasks that were running or waiting on this worker will show incorrect
    state. Any reserved_resource reservations associated with the previous worker will also be
    removed along with the worker entry in the database itself. This is called early in the worker
    start process, and later when its fully online pulp_celerybeat will discover the worker as
    usual to allow new work to arrive at this worker.

    If there is no previous work to cleanup this method still runs, but has not effect on the
    database.

    :param args: For positional arguments; and not used otherwise
    :param kwargs: For keyword arguments, and expected to have one named 'sender'
    :return: None
    """
    name = kwargs['sender'].hostname
    _delete_worker(name, normal_shutdown=True)
