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
from gettext import gettext as _
import logging
import random
import re

from celery import chain, task, Task as CeleryTask
from celery.app import control, defaults

from pulp.common import dateutils
from pulp.server.async.celery_instance import celery, RESOURCE_MANAGER_QUEUE
from pulp.server.async.task_status_manager import TaskStatusManager
from pulp.server.db.model.criteria import Criteria
from pulp.server.db.model.dispatch import TaskStatus
from pulp.server.db.model.resources import AvailableQueue, DoesNotExist, ReservedResource
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.managers import resources


controller = control.Control(app=celery)
logger = logging.getLogger(__name__)


RESERVED_WORKER_NAME_PREFIX = 'reserved_resource_worker-'


# TODO: We must find a way to deal with the situation where babysit() tasks have piled up in the
#       RESOURCE_MANAGER_QUEUE due to no worker listening to it. Remembering the last time we
#       babysat and skipping if it was too recent might be a good way to do it.
# TODO: Convert the babysit() Task to accept the results of the active_queues() output, and create
#       a new Task to generate that data and pass it to babysit(). This will keep our reservation
#       queue from having tasks that take too long in it (active_queues() can take seconds to
#       complete.)
@task
def babysit():
    """
    Babysit the workers, updating our tables with information about their queues.
    """
    # Inspect the available workers to build our state variables
    active_queues = controller.inspect().active_queues()
    reserved_queues = []
    for worker, queues in active_queues.items():
        # If this worker is a reserved task worker, let's make sure we know about it in our
        # available_queues collection, and make sure it is processing a queue with its own name
        if re.match('^%s' % RESERVED_WORKER_NAME_PREFIX, worker):
            # Make sure that this worker is subscribed to a queue of his own name. If not,
            # subscribe him to one
            if not worker in [queue['name'] for queue in queues]:
                controller.add_consumer(queue=worker, destination=(worker,))
            # Now let's make sure this worker's queue is included in our available_queues
            # collection
            resources.get_or_create_available_queue(worker)
            reserved_queues.append(worker)
            # TODO: See if we can detect and/or set the worker's concurrency to 1 here

    # Now we must delete queues for workers that don't exist anymore
    missing_queue_criteria = Criteria(filters={'_id': {'$nin': reserved_queues}})
    available_queues_missing_workers = resources.filter_available_queues(
        missing_queue_criteria)
    for queue in available_queues_missing_workers:
        # TODO: DON'T REMOVE QUEUES UNLESS IT HAS BEEN LONG ENOUGH SINCE WE LAST SAW THEM (5
        #       minutes is the suggested timeout.
        # TODO: Also delete the queues themselves from the broker when deleting them here.
        # TODO: Also delete the queues from the reserved_resources collection so that no new
        #       tasks enter them

        msg = _('The worker named %(name)s is missing. Canceling the tasks in its queue.')
        msg = msg % {'name': queue}
        logger.error(msg)
        # Cancel all of the tasks that were assigned to this queue
        for task in TaskStatusManager.find_by_criteria(Criteria(filters={'queue': queue.name})):
            cancel(task['task_id'])
        # Finally, delete the queue
        queue.delete()


@task
def _queue_release_resource(resource_id):
    """
    This function will queue the _release_resource() task in the resource manager's queue for the
    given resource_id. It is necessary to have this function in addition to the _release_resource()
    function because we typically do not want to queue the _release_resource() task until the task
    that is using the resource is finished. Therefore, when queuing a function that reserves a
    resource, you should always queue a call to this function after it, and it is important that you
    queue this task in the same queue that the resource reserving task is being performed in so that
    it happens afterwards. You should not queue the _release_resource() task yourself.

    :param resource_id: The resource_id that you wish to release
    :type  resource_id: basestring
    """
    _release_resource.apply_async(args=(resource_id,), queue=RESOURCE_MANAGER_QUEUE)


@task
def _release_resource(resource_id):
    """
    Do not queue this task yourself, but always use the _queue_release_resource() task instead.
    Please see the docblock on that function for an explanation.

    When a resource-reserving task is complete, this method must be called with the
    resource_id so that the we know when it is safe to unmap a resource_id from
    its given queue name.

    :param resource_id: The resource that is no longer in use
    :type  resource_id: basestring
    """
    try:
        reserved_resource = ReservedResource(resource_id)
        reserved_resource.decrement_num_reservations()
        # Now we need to decrement the AvailabeQueue that the reserved_resource was using. If the
        # ReservedResource does not exist for some reason, we won't know its assigned_queue, but
        # these next lines won't execute anyway.
        available_queue = AvailableQueue(reserved_resource.assigned_queue)
        available_queue.decrement_num_reservations()
    except DoesNotExist:
        # If we are trying to decrement the count on one of these obejcts, and they don't exist,
        # that's OK
        pass


@task
def _reserve_resource(resource_id):
    """
    When you wish you queue a task that needs to reserve a resource, you should make a call to this
    function() first, queueing it in the RESOURCE_MANAGER_QUEUE. This Task will return the
    name of the queue you should put your task in.

    Please be sure to also add a task to run _queue_release_resource() in the same queue name that
    this function returns to you. It is important that _release_resource() is called after your task
    is completed, regardless of whether your task completes successfully or not.

    :param resource_id: The name of the resource you wish to reserve for your task. The system
                        will ensure that no other tasks that want that same reservation will run
                        concurrently with yours.
    :type  resource_id: basestring
    :return:            The name of a queue that you should put your task in
    :rtype:             basestring
    """
    reserved_resource = resources.get_or_create_reserved_resource(resource_id)
    if reserved_resource.assigned_queue is None:
        # The assigned_queue will be None if the reserved_resource was just created, so we'll
        # need to assign a queue to it
        reserved_resource.assigned_queue = resources.get_least_busy_available_queue().name
        reserved_resource.save()
    else:
        # The assigned_queue is set, so we just need to increment the num_reservations on the
        # reserved resource
        reserved_resource.increment_num_reservations()

    AvailableQueue(reserved_resource.assigned_queue).increment_num_reservations()
    return reserved_resource.assigned_queue


class ReservedTaskMixin(object):
    def apply_async_with_reservation(self, resource_id, *args, **kwargs):
        """
        This method allows the caller to schedule the ReservedTask to run asynchronously just like
        Celery's apply_async(), while also making the named resource. No two tasks that claim the
        same resource reservation can execute concurrently.

        For a list of parameters accepted by the *args and **kwargs parameters, please see the
        docblock for the apply_async() method.

        :param resource_id: A string that identifies some named resource, guaranteeing that only one
                            task reserving this same string can happen at a time.
        :type  resource_id: basestring
        :param tags:        A list of tags (strings) to place onto the task, used for searching for
                            tasks by tag
        :type  tags:        list
        :return:            An AsyncResult instance as returned by Celery's apply_async
        :rtype:             celery.result.AsyncResult
        """
        queue = _reserve_resource.apply_async((resource_id,), queue=RESOURCE_MANAGER_QUEUE).get()

        kwargs['queue'] = queue

        async_result = self.apply_async(*args, **kwargs)
        _queue_release_resource.apply_async((resource_id,), queue=queue)

        return async_result


class Chain(chain, ReservedTaskMixin):
    """
    This is a custom Pulp subclass of the Celery chain class. It allows us to inject resource
    locking behaviors into the Chain.
    """
    pass


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
        queue = kwargs.get('queue', defaults.NAMESPACES['CELERY']['DEFAULT_QUEUE'].default)
        tags = kwargs.pop('tags', [])
        async_result = super(Task, self).apply_async(*args, **kwargs)

        # Create a new task status with the task id and tags.
        # To avoid the race condition where __call__ method below is called before
        # this change is propagated to all db nodes, using an 'upsert' here and setting
        # the task state to 'waiting' only on an insert.
        TaskStatus.get_collection().update(
            {'task_id': async_result.id},
            {'$setOnInsert': {'state':dispatch_constants.CALL_WAITING_STATE},
             '$set': {'queue': queue, 'tags': tags}},
            upsert=True)
        return async_result

    def __call__(self, *args, **kwargs):
        """
        This overrides CeleryTask's __call__() method. We use this method
        for task state tracking of Pulp tasks.
        """
        # Updates start_time and sets the task state to 'running' for asynchronous tasks.
        # Skip updating status for eagerly executed tasks, since we don't want to track
        # synchronous tasks in our database.
        if not self.request.called_directly:
            # Using 'upsert' to avoid a possible race condition described in the apply_async method
            # above.
            TaskStatus.get_collection().update(
                {'task_id': self.request.id},
                {'$set': {'state': dispatch_constants.CALL_RUNNING_STATE,
                          'start_time':  dateutils.now_utc_timestamp()}},
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
            delta = {'state': dispatch_constants.CALL_FINISHED_STATE,
                     'finish_time': dateutils.now_utc_timestamp(),
                     'result': retval}
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
            delta = {'state': dispatch_constants.CALL_ERROR_STATE,
                     'finish_time': dateutils.now_utc_timestamp(),
                     'traceback': einfo.traceback}
            TaskStatusManager.update_task_status(task_id=task_id, delta=delta)


def cancel(task_id):
    """
    Cancel the task that is represented by the given task_id.

    :param task_id: The ID of the task you wish to cancel
    :type  task_id: basestring
    """
    controller.revoke(task_id, terminate=True)
    msg = _('Task canceled: %(task_id)s.')
    msg = msg % {'task_id': task_id}
    logger.info(msg)
