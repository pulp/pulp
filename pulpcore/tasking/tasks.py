import logging
import time
import uuid
from gettext import gettext as _

from django.db import IntegrityError
from rq import Queue
from rq.job import get_current_job, Job

from pulpcore.app.models import Task, ReservedResource, Worker
from pulpcore.constants import TASK_STATES
from pulpcore.tasking import connection, util


_logger = logging.getLogger(__name__)


# workaround for long-running tasks https://github.com/rq/rq/issues/872
# Pulp tasks should never run more than one Julian year
TASK_TIMEOUT = 31557600


def _acquire_worker(resources):
    """
    Attempts to acquire a worker for a set of resource urls. If no worker has any of those resources
    reserved, then the first available worker is returned

    Arguments:
        resources (list): a list of resource urls

    Returns:
        :class:`pulpcore.app.models.Worker`: A worker to queue work for

    Raises:
        Worker.DoesNotExist: If no worker is found
    """
    # Find a worker who already has this reservation, it is safe to send this work to them
    try:
        worker = Worker.objects.with_reservations(resources)
    except Worker.MultipleObjectsReturned:
        raise Worker.DoesNotExist
    except Worker.DoesNotExist:
        pass
    else:
        return worker

    # Otherwise, return any available worker
    return Worker.objects.get_unreserved_worker()


def _queue_reserved_task(func, inner_job_id, resources, inner_args, inner_kwargs, options):
    """
    A task that encapsulates another task to be dispatched later.

    This task being encapsulated is called the "inner" task, and a task name, UUID, and accepts a
    list of positional args and keyword args for the inner task. These arguments are named
    inner_args and inner_kwargs. inner_args is a list, and inner_kwargs is a dictionary passed to
    the inner task as positional and keyword arguments using the * and ** operators.

    The inner task is dispatched into a dedicated queue for a worker that is decided at dispatch
    time. The logic deciding which queue receives a task is controlled through the
    find_worker function.

    Args:
        func (basestring): The function to be called
        inner_job_id (basestring): The job_id to be set on the task being called. By providing
            the UUID, the caller can have an asynchronous reference to the inner task
            that will be dispatched.
        resources (basestring): The urls of the resource you wish to reserve for your task.
            The system will ensure that no other tasks that want that same reservation will run
            concurrently with yours.
        inner_args (tuple): The positional arguments to pass on to the task.
        inner_kwargs (dict): The keyword arguments to pass on to the task.
        options (dict): For all options accepted by enqueue see the RQ docs
    """
    redis_conn = connection.get_redis_connection()
    task_status = Task.objects.get(job_id=inner_job_id)
    task_name = func.__module__ + '.' + func.__name__
    while True:
        if task_name == "pulpcore.app.tasks.orphan.orphan_cleanup":
            if ReservedResource.objects.exists():
                # wait until there are no reservations
                time.sleep(0.25)
                continue
            else:
                task_status.state = TASK_STATES.RUNNING
                task_status.save()
                q = Queue('resource_manager', connection=redis_conn, is_async=False)
                q.enqueue(func, args=inner_args, kwargs=inner_kwargs, job_id=inner_job_id,
                          timeout=TASK_TIMEOUT, **options)
                task_status.state = TASK_STATES.COMPLETED
                task_status.save()
                return

        try:
            worker = _acquire_worker(resources)
        except Worker.DoesNotExist:
            # no worker is ready so we need to wait
            time.sleep(0.25)
            continue

        try:
            worker.lock_resources(task_status, resources)
        except IntegrityError:
            # we have a worker but we can't create the reservations so wait
            time.sleep(0.25)
        else:
            # we have a worker with the locks
            break

    task_status.worker = worker
    task_status.save()

    try:
        q = Queue(worker.name, connection=redis_conn)
        q.enqueue(func, args=inner_args, kwargs=inner_kwargs, job_id=inner_job_id,
                  timeout=TASK_TIMEOUT, **options)
    finally:
        q.enqueue(_release_resources, args=(inner_job_id, ))


def _release_resources(job_id):
    """
    Do not queue this task yourself. It will be used automatically when your task is dispatched by
    the _queue_reserved_task task.

    When a resource-reserving task is complete, this method releases the task's resource(s)

    Args:
        job_id (basestring): The job_id of the task that requested the reservation

    """
    try:
        task = Task.objects.get(job_id=job_id, state=TASK_STATES.RUNNING)
    except Task.DoesNotExist:
        pass
    else:
        msg = _('The task {task_id} exited immediately for some reason. Marking as '
                'failed. Check the logs for more details')
        _logger.error(msg.format(task_id=task.pk))
        exc = RuntimeError(msg.format(task_id=task.pk))
        task.set_failed(exc, None)

    Task.objects.get(job_id=job_id).release_resources()


def enqueue_with_reservation(func, resources, args=None, kwargs=None, options=None):
    """
    Enqueue a message to Pulp workers with a reservation.

    This method provides normal enqueue functionality, while also requesting necessary locks for
    serialized urls. No two tasks that claim the same resource can execute concurrently. It
    accepts resources which it transforms into a list of urls (one for each resource).

    This does not dispatch the task directly, but instead promises to dispatch it later by
    encapsulating the desired task through a call to a :func:`_queue_reserved_task` task. See
    the docblock on :func:`_queue_reserved_task` for more information on this.

    This method creates a :class:`pulpcore.app.models.Task` object. Pulp expects to poll on a
    task just after calling this method, so a Task entry needs to exist for it
    before it returns.

    Args:
        func (callable): The function to be run by RQ when the necessary locks are acquired.
        resources (list): A list of resources to reserve guaranteeing that only one task
            reserves these resources
        args (tuple): The positional arguments to pass on to the task.
        kwargs (dict): The keyword arguments to pass on to the task.
        options (dict): The options to be passed on to the task.

    Returns (rq.job.job): An RQ Job instance as returned by RQ's enqueue function
    """
    if not args:
        args = tuple()
    if not kwargs:
        kwargs = dict()
    if not options:
        options = dict()

    resources = {util.get_url(resource) for resource in resources}
    inner_job_id = str(uuid.uuid4())
    redis_conn = connection.get_redis_connection()
    current_job = get_current_job(connection=redis_conn)
    parent_kwarg = {}
    if current_job:
        current_task = Task.objects.get(job_id=current_job.id)
        parent_kwarg['parent'] = current_task
    Task.objects.create(job_id=inner_job_id, state=TASK_STATES.WAITING, **parent_kwarg)
    q = Queue('resource_manager', connection=redis_conn)
    task_args = (func, inner_job_id, list(resources), args, kwargs, options)
    q.enqueue(_queue_reserved_task, args=task_args, timeout=TASK_TIMEOUT)
    return Job(id=inner_job_id, connection=redis_conn)
