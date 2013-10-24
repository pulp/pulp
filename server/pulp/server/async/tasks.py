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
import random

from celery import chain, task, Task as CeleryTask
from celery.app import control

from pulp.server.async.celery_instance import celery


DEFAULT_CELERY_QUEUE = 'celery'
RESOURCE_MANAGER_QUEUE = 'resource_manager'


controller = control.Control(app=celery)
# The singleton ResourceManager will be stored here when and if it is instantiated. Only one worker
# should do this.
_resource_manager = None


class NoAvailableQueues(Exception):
    """
    This Exception is raised by ResourceManager._get_workers_available_queue_stats() if the given
    worker does not have any available queues for reserved work. It can also be raised by
    ResourceManager._get_available_queue() if no queues can be found in the system.
    """
    pass


class ResourceManager(object):
    """
    Do not instantiate this object yourself! It must be a singleton. You can get the singleton
    instance from the _get_resource_manager() function. Also, do not use the ResourceManager
    directly unless you have thought about what you are doing very carefully. You should generally
    only use the _reserve_resource() and _queue_release_resource() functions from this module
    instead of the ResourceManager's methods.

    The ResourceManager exists to help ensure that tasks that need to happen sequentially do not get
    processed in parallel. It is important that this class be a singleton across the entire Pulp
    installation, which can only be guaranteed if only one Celery worker is subscribed to work on
    tasks in the special named queue, RESOURCE_MANAGER_QUEUE, and that Celery worker has its
    concurrency set to 1.
    """
    def __init__(self):
        """
        Do not instantiate this object yourself! It must be a singleton. You can get the singleton
        instance from the _get_resource_manager() function.

        Inspect the existing workers and the queues they are subscribed to. This information will be
        used to initialize the ResourceManager's state tables that it will use to route reserved
        tasks to the appropriate queues.
        """
        # Map available queue names to their current loads
        self._available_queue_task_counts = {}
        # Map worker names to a list of reserved task queues that they are assigned to
        self._worker_queues = {}
        # Map resource_ids to the queue they are supposed to go to, and the number of tasks that
        # are in that queue that will lock the resource
        self._resource_map = {}

        # Inspect the available workers to build our state variables
        active_queues = controller.inspect().active_queues()
        for worker, queues in active_queues.items():
            self._worker_queues[worker] = []
            for queue in queues:
                # If the queue in question is not the normal celery queue or the special resource
                # manager queue, it is assumed to be a reserved instance queue
                if queue['name'] not in [DEFAULT_CELERY_QUEUE, RESOURCE_MANAGER_QUEUE]:
                    self._available_queue_task_counts[queue['name']] = 0
                    self._worker_queues[worker].append(queue['name'])
            # If the worker doesn't have any reserved task queues, let's remove it from our worker
            # table
            if self._worker_queues[worker] == []:
                del self._worker_queues[worker]

    def release_resource(self, resource_id):
        """
        When a resource-reserving task is complete, this method must be called with the
        resource_id so that the ResourceManager knows when it is safe to unmap a resource_id from
        its given queue name.

        :param resource_id: The resource that is no longer in use
        :type  resource_id: basestring
        """
        try:
            self._resource_map[resource_id]['task_count'] -= 1
            # Let's keep from going negative on our queue task counts. This could happen if the
            # ResourceManager is restarted when the queue lengths were non-zero, since it
            # initializes the queue counts to 0.
            if self._available_queue_task_counts[self._resource_map[resource_id]['queue']]:
                self._available_queue_task_counts[self._resource_map[resource_id]['queue']] -= 1

            if not self._resource_map[resource_id]['task_count']:
                del self._resource_map[resource_id]
        except KeyError:
            # If we are asked to release a resource that we don't have reserved, it is weird, but we
            # don't want to raise an Exception about it because our state does have that resource
            # unreserved. This could happen, for example, if the ResourceManager is restarted while
            # there is already work in queues.
            pass

    def reserve_resource(self, resource_id):
        """
        Return the name of a Celery queue that can be used to queue tasks that use the given
        resource_id.

        :param resource_id: The ID of the resource that the caller wishes to process in a job queue
        :type  resource_id: basestring
        :return:            The name of a Celery queue that the task that wishes to use the given
                            resource_id should be queued inside of.
        :rtype:             basestring
        """
        if resource_id in self._resource_map:
            self._resource_map[resource_id]['task_count'] += 1
            queue = self._resource_map[resource_id]['queue']
        else:
            queue = self._get_available_queue()
            self._resource_map[resource_id] = {'queue': queue, 'task_count': 1}

        self._available_queue_task_counts[queue] += 1
        return queue

    def _get_available_queue(self):
        """
        Find the worker with the fewest assigned tasks, and return a queue name that is assigned to
        that worker.

        :return: The name of an available queue
        :rtype:  basestring
        """
        least_busy_worker_task_count = None
        least_busy_worker_queue = None
        # We want to consider the workers in a random order, so that we don't always choose the same
        # workers when there is a tie for the least busy worker.
        workers = self._worker_queues.keys()
        random.shuffle(workers)
        # Loop over our available workers, comparing them to find the least busy one
        for worker in workers:
            try:
                stats = self._get_workers_available_queue_stats(worker)
            except NoAvailableQueues:
                # If this worker doesn't have any available queues, let's continue
                continue
            # If this worker is less busy than the least busy one we've found so far, or if it's the
            # first worker we've found with an available queue, mark it.
            if stats['num_tasks'] < least_busy_worker_task_count \
                    or least_busy_worker_task_count is None:
                least_busy_worker_task_count = stats['num_tasks']
                least_busy_worker_queue = stats['least_busy_queue']

        if least_busy_worker_queue is None:
            msg = _('There are no available queues in the system for reserved task work.')
            raise NoAvailableQueues(msg)
        return least_busy_worker_queue

    def _get_workers_available_queue_stats(self, worker):
        """
        Given a worker's name, find out how many tasks are assigned to it by considering the queues
        it's assigned to work on that are also in our self._available_queue_task_counts table.
        Return a dictionary that includes the total number of tasks found in the workers available
        queues, as well as the name of its least busy queue. These are indexed by 'num_tasks' and
        'least_busy_queue', respectively.

        :param worker: The name of the worker we need a task count for
        :type  worker: basestring
        :return:       A dictionary with two keys. 'least_busy_queue' indexes a string naming the
                       worker's least busy queue name. 'num_tasks' indexes an int measuring the
                       total tasks across all available queues assigned to the worker.
        :rtype:        dict
        """
        return_value = {'least_busy_queue': None, 'num_tasks': 0}
        least_busy_queue_task_count = None

        for queue in self._worker_queues[worker]:
            # Inspect each queue for the worker, checking to see if it is in our available_queues
            # structure. If it is, compare it to the least busy queue we've found so far and also
            # increment the num_tasks for this worker. If this is the least_busy queue we've seen so
            # far, remember it.
            if queue in self._available_queue_task_counts.keys():
                return_value['num_tasks'] += self._available_queue_task_counts[queue]
                if self._available_queue_task_counts[queue] < least_busy_queue_task_count \
                        or least_busy_queue_task_count is None:
                    least_busy_queue_task_count = self._available_queue_task_counts[queue]
                    return_value['least_busy_queue'] = queue
        if return_value['least_busy_queue'] is None:
            msg = _('The worker %(w)s does not have any available reserved queues.')
            msg = msg % {'w': worker}
            raise NoAvailableQueues(msg)
        return return_value


def _get_resource_manager():
    """
    We need the ResourceManager to be a singleton, since it needs to keep track of which resources
    are assigned to which queues, and which queues are assigned to which workers. This function
    helps us to achieve the singleton instance for this process, as it checks to see if there is
    already a ResourceManager instance in this module, and returns it if there is. If there is not,
    it instantiates one, assigns it to the module, and then returns it. If you need a
    ResourceManager instance, you should always use this function.

    :return: A ResourceManager instance
    :rtype:  pulp.server.async.tasks.ResourceManager
    """
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager


@task
def _queue_release_resource(resource_id):
    """
    This function will queue the _release_resource() task in the ResourceManager's queue for the
    given resource_id. It is necessary to have this function in addition to the _release_resource()
    function because we typically do not want to queue the _release_resource() task until the task
    that is using the resource is finished. Therefore, when queuing a function that reserves a
    resource, you should always queue a call to this function after it, and it is important that you
    queue this task in the same queue that the resource reserving task is being performed in so that
    it happens afterwards. You should not queue the _release_resource() task yourself. It is also
    important that you do not use the ResourceManager itself for releasing resources.

    :param resource_id: The resource_id that you wish to release with the ResourceManager singleton
    :type  resource_id: basestring
    """
    _release_resource.apply_async(args=(resource_id,), queue=RESOURCE_MANAGER_QUEUE)


@task
def _release_resource(resource_id):
    """
    Do not queue this task yourself, but always use the _queue_release_resource() task instead.
    Please see the docblock on that function for an explanation.

    This Task will call the release_resource() method on the singleton ResourceManager instance with
    the given resource_id.

    :param resource_id: The resource_id that you wish to release with the ResourceManager singleton
    :type  resource_id: basestring
    """
    _get_resource_manager().release_resource(resource_id)


@task
def _reserve_resource(resource_id):
    """
    When you wish you queue a task that needs to reserve a resource, you should make a call to this
    function() first, queueing it in the RESOURCE_MANAGER_QUEUE. The ResourceManager will return the
    name of the queue you should put your task in.

    Please be sure to also add a task to run _queue_release_resource() in the same queue name that
    this function returns to you. It is important that _release_resource() is called after your task
    is completed, regardless of whether your task completes successfully or not.

    :param resource_id: The name of the resource you wish to reserve for your task. The
                        ResourceManager will ensure that no other tasks that want that same
                        reservation will run concurrently with yours.
    :type  resource_id: basestring
    :return:            The name of a queue that you should put your task in
    :rtype:             basestring
    """
    return _get_resource_manager().reserve_resource(resource_id)


class ReservedTask(object):
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


class Chain(chain, ReservedTask):
    """
    This is a custom Pulp subclass of the Celery chain class. It allows us to inject resource
    locking behaviors into the Chain.
    """
    pass


class Task(CeleryTask, ReservedTask):
    """
    This is a custom Pulp subclass of the Celery Task object. It allows us to inject some custom
    behavior into each Pulp task, including management of resource locking.
    """
    def apply_async(self, *args, **kwargs):
        """
        A wrapper around the Celery apply_async method. It allows us to accept a few more
        parameters than Celery does for our own purposes, listed below.

        :param tags:        A list of tags (strings) to place onto the task, used for searching for
                            tasks by tag
        :type  tags:        list
        :return:            An AsyncResult instance as returned by Celery's apply_async
        :rtype:             celery.result.AsyncResult
        """
        tags = kwargs.pop('tags', [])

        return super(Task, self).apply_async(*args, **kwargs)


def cancel(task_id):
    """
    Cancel the task that is represented by the given task_id.

    :param task_id: The ID of the task you wish to cancel
    :type  task_id: basestring
    """
    controller.revoke(task_id, terminate=True)
