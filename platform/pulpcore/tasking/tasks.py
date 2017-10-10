import cProfile
import errno
import logging
import os
import time
import uuid
from gettext import gettext as _

from celery import Task as CeleryTask
from celery import task
from celery.app import control
from celery.result import AsyncResult
from django.conf import settings as pulp_settings
from django.db import IntegrityError, transaction

from pulpcore.app.models import Task as TaskStatus
from pulpcore.app.models import ReservedResource, Worker
from pulpcore.common import TASK_STATES
from pulpcore.exceptions import PulpException
from pulpcore.tasking import util
from pulpcore.tasking.celery_instance import (DEDICATED_QUEUE_EXCHANGE, RESOURCE_MANAGER_QUEUE,
                                              celery)

celery_controller = control.Control(app=celery)
_logger = logging.getLogger(__name__)


class PulpTask(CeleryTask):
    """
    The ancestor of all Celery tasks in Pulp. Use the 'base' argument to specify this task as its
    parent. For example:

        >>> from celery import task
        >>> @task(base=PulpTask, acks_late=True)
        >>> def sum(a, b):
        >>>     return a + b

    This object provides a centralized place to put behavioral changes which should affect all
    tasks.
    """
    pass


@task(base=PulpTask, acks_late=True)
def _queue_reserved_task(name, inner_task_id, resource_id, inner_args, inner_kwargs, options):
    """
    A task that encapsulates another task to be dispatched later. This task being encapsulated is
    called the "inner" task, and a task name, UUID, and accepts a list of positional args
    and keyword args for the inner task. These arguments are named inner_args and inner_kwargs.
    inner_args is a list, and inner_kwargs is a dictionary passed to the inner task as positional
    and keyword arguments using the * and ** operators.

    The inner task is dispatched into a dedicated queue for a worker that is decided at dispatch
    time. The logic deciding which queue receives a task is controlled through the
    find_worker function.

    Args:
        name (basestring): The name of the task to be called
        inner_task_id (basestring): The UUID to be set on the task being called. By providing
            the UUID, the caller can have an asynchronous reference to the inner task
            that will be dispatched.
        resource_id (basestring): The name of the resource you wish to reserve for your task.
            The system will ensure that no other tasks that want that same reservation will run
            concurrently with yours.
        inner_args (tuple): The positional arguments to pass on to the task.
        inner_kwargs (dict): The keyword arguments to pass on to the task.
        options (dict): For all options accepted by apply_async please visit: http://docs.celeryproject.org/en/latest/reference/celery.app.task.html#celery.app.task.Task.apply_async  # noqa

    Returns:
        An AsyncResult instance as returned by Celery's apply_async
    """
    while True:
        # Find a worker who already has this reservation, it is safe to send this work to them
        try:
            worker = ReservedResource.objects.filter(resource=resource_id)[0].worker
        except IndexError:
            pass
        else:
            break

        try:
            worker = Worker.objects.get_unreserved_worker()
        except Worker.DoesNotExist:
            pass
        else:
            break

        # No worker is ready for this work, so we need to wait
        time.sleep(0.25)

    task_status = TaskStatus.objects.get(pk=inner_task_id)
    task_status.worker = worker
    task_status.save()
    ReservedResource.objects.create(task=task_status, worker=worker, resource=resource_id)

    try:
        celery.tasks[name].apply_async(args=inner_args, task_id=inner_task_id,
                                       routing_key=worker.name, exchange=DEDICATED_QUEUE_EXCHANGE,
                                       kwargs=inner_kwargs, **options)
    finally:
        _release_resource.apply_async(args=(inner_task_id, ), routing_key=worker.name,
                                      exchange=DEDICATED_QUEUE_EXCHANGE)


@task(base=PulpTask)
def _release_resource(task_id):
    """
    Do not queue this task yourself. It will be used automatically when your task is dispatched by
    the _queue_reserved_task task.

    When a resource-reserving task is complete, this method releases the resource by removing the
    ReservedResource object by UUID.

    Args:
        task_id (basestring): The UUID of the task that requested the reservation

    """
    try:
        TaskStatus.objects.get(pk=task_id, state=TASK_STATES.RUNNING)
    except TaskStatus.DoesNotExist:
        pass
    else:
        new_task = PulpTask()
        msg = _('The task status %(task_id)s exited immediately for some reason. Marking as '
                'failed. Check the logs for more details')
        runtime_exception = RuntimeError(msg % {'task_id': task_id})

        class MyEinfo(object):
            traceback = None

        new_task.on_failure(runtime_exception, task_id, (), {}, MyEinfo)

    ReservedResource.objects.filter(task__pk=task_id).delete()


class UserFacingTask(PulpTask):
    """
    A Pulp Celery task which will be visible to the user through the tasking portion of the API.

    This object provides two interfaces to dispatch tasks: :meth:`apply_async` and
    :meth:`apply_async_with_reservation`.

    The :meth:`apply_asyc` provides normal celery dispatches of the task to the 'celery' queue
    which all workers subscribe to. The task is handled by the first available worker.

    The :meth:`apply_async_with_reservation` dispatch interface will send the task through the
    resource_manager queue and process and will be assigned a specific worker. A series of
    reservations cause specific types of tasks to not be run concurrently. See the
    :meth:`apply_async_with_reservation` documentation for more details.
    """

    # this tells celery to not automatically log tracebacks for these exceptions
    throws = (PulpException,)

    def apply_async_with_reservation(self, resource_type, resource_id, tags=[], group_id=None,
                                     args=None, kwargs=None, **options):
        """
        This method provides normal apply_async functionality, while also serializing tasks by
        resource name. No two tasks that claim the same resource name can execute concurrently. It
        accepts resource_type and resource_id and combines them to form a reservation key.

        This does not dispatch the task directly, but instead promises to dispatch it later by
        encapsulating the desired task through a call to a :func:`_queue_reserved_task` task. See
        the docblock on :func:`_queue_reserved_task` for more information on this.

        This method creates a :class:`pulpcore.app.models.Task` object. Pulp expects to poll on a
        task just after calling this method, so a Task entry needs to exist for it
        before it returns.

        Args:
            resource_type (basestring): A string that identifies type of a resource
            resource_id (basestring): A string that identifies some named resource, guaranteeing
                that only one task reserving this same string can happen at a time.
            tags (list): A list of tags (strings) to place onto the task, used for searching
                for tasks by tag. This is an optional argument which is pulled out of kwargs.
            group_id (uuid.UUID): The id to identify which group of tasks a task belongs to.
                This is an optional argument which is pulled out of kwargs.
            args (tuple): The positional arguments to pass on to the task.
            kwargs (dict): The keyword arguments to pass on to the task.
            options (dict): For all options accepted by apply_async please visit: http://docs.celeryproject.org/en/latest/reference/celery.app.task.html#celery.app.task.Task.apply_async  # noqa

        Returns (celery.result.AsyncResult):
            An AsyncResult instance as returned by Celery's apply_async
        """
        # Form a resource_id for reservation by combining given resource type and id. This way,
        # two different resources having the same id will not block each other.
        resource_id = ":".join((resource_type, resource_id))
        inner_task_id = str(uuid.uuid4())
        task_name = self.name

        # Set the parent attribute if being dispatched inside of a Task
        parent_arg = self._get_parent_arg()

        # Create a new task status with the task id and tags.
        with transaction.atomic():
            task_status = TaskStatus.objects.create(pk=inner_task_id, state=TaskStatus.WAITING,
                                                    group=group_id, **parent_arg)
            for tag in tags:
                task_status.tags.create(name=tag)

        # Call the outer task which is a promise to call the real task when it can.
        _queue_reserved_task.apply_async(args=(task_name, inner_task_id, resource_id, args,
                                               kwargs, options),
                                         queue=RESOURCE_MANAGER_QUEUE)
        return AsyncResult(inner_task_id)

    def apply_async(self, tags=[], group_id=None, args=None, kwargs=None, **options):
        """
        A wrapper around the super() apply_async method. It allows us to accept a few more
        arguments than Celery does for our own purposes, listed below. It also allows us
        to create and update task status which can be used to track status of this task
        during it's lifetime.

        Args:
            tags (list): A list of tags (strings) to place onto the task, used for searching for
                tasks by tag
            group_id (uuid.UUID): The id that identifies which group of tasks a task belongs to
            args (tuple): The positional arguments to pass on to the task.
            kwargs (dict): The keyword arguments to pass on to the task.
            options (dict): For all options accepted by apply_async please visit: http://docs.celeryproject.org/en/latest/reference/celery.app.task.html#celery.app.task.Task.apply_async  # noqa

        Returns (celery.result.AsyncResult):
            An AsyncResult instance as returned by Celery's apply_async
        """

        async_result = super(UserFacingTask, self).apply_async(args=args, kwargs=kwargs, **options)

        # Set the parent attribute if being dispatched inside of a Task
        parent_arg = self._get_parent_arg()

        # Create a new task status with the task id and tags.
        with transaction.atomic():
            try:
                task_status = TaskStatus.objects.create(pk=async_result.id,
                                                        state=TaskStatus.WAITING,
                                                        group=group_id, **parent_arg)
            except IntegrityError:
                # The TaskStatus was already created with the call to apply_async_with_reservation
                pass
            else:
                for tag in tags:
                    task_status.tags.create(name=tag)

        return async_result

    def __call__(self, *args, **kwargs):
        """
        Called on the worker just before the task begins executing.

        Set the :class:`pulpcore.app.models.Task` object in the running state,
        associate the worker, and log a message.
        """
        task_status = TaskStatus.objects.get(pk=self.request.id)
        task_status.set_running()

        try:
            worker = Worker.objects.get(name=self.request.hostname)
        except Worker.DoesNotExist:
            _logger.warning(_("Failed to find worker with hostname {host}").format(
                host=self.request.hostname))
        else:
            if not task_status.worker:
                task_status.worker = worker
                task_status.save()

        _logger.debug(_("Running task : [%s]") % self.request.id)

        if pulp_settings.PROFILING['enabled'] is True:
            self.pr = cProfile.Profile()
            self.pr.enable()

        return super(UserFacingTask, self).__call__(*args, **kwargs)

    def on_success(self, retval, task_id, args, kwargs):
        """
        Update the :class:`pulpcore.app.models.Task` object, log, and save the result.

        Skip the status updating if the callback is called synchronously.

        Args:
            retval: The return value of the task.
            task_id (:class:`uuid.UUID`): Unique id of the executed task.
            args (list): Original arguments for the executed task.
            kwargs (dict): Original keyword arguments for the executed task.

        """
        _logger.debug("Task successful : [%s]" % task_id)
        if not self.request.called_directly:
            task_status = TaskStatus.objects.get(pk=task_id)
            task_status.set_completed(retval)

            self._handle_cProfile(task_id)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Update the :class:`pulpcore.app.models.Task` object, log, and save the results.

        Skip the status updating if the callback is called synchronously.

        Args:
            exc (BaseException): The exception raised by the task.
            task_id (:class:`uuid.UUID`): Unique id of the failed task.
            args (list): Original arguments for the executed task.
            kwargs (dict): Original keyword arguments for the executed task.
            einfo: celery's ExceptionInfo instance, containing serialized traceback.
        """
        _logger.error(_('Task failed : [%s]') % task_id)
        if isinstance(exc, PulpException):
            _logger.exception(exc)

        if not self.request.called_directly:
            task_status = TaskStatus.objects.get(pk=task_id)
            task_status.set_failed(exc, einfo)

            self._handle_cProfile(task_id)

    def _get_parent_arg(self):
        """Return a dictionary with the 'parent' set if running inside of a UserFacingTask"""
        parent_arg = {}
        current_task_id = util.get_current_task_id()
        if current_task_id is not None:
            try:
                current_task_obj = TaskStatus.objects.get(pk=current_task_id)
            except TaskStatus.DoesNotExist:
                pass
            else:
                parent_arg['parent'] = current_task_obj
        return parent_arg

    def _handle_cProfile(self, task_id):
        """
        If cProfiling is enabled, stop the profiler and write out the data.

        Args:
            task_id (unicode): the id of the task

        """
        if pulp_settings.PROFILING['enabled'] is True:
            self.pr.disable()
            profile_directory = pulp_settings.PROFILING['directory']
            try:
                os.makedirs(profile_directory, mode=0o755)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
            self.pr.dump_stats("%s/%s" % (profile_directory, task_id))
