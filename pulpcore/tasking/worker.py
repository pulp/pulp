import logging
import os
import signal
import socket
import sys
import threading
import time

# https://github.com/rochacbruno/dynaconf/issues/89
from dynaconf.contrib import django_dynaconf  # noqa

from rq import Queue
from rq.worker import Worker


import django  # noqa otherwise E402: module level not at top of file
django.setup()  # noqa otherwise E402: module level not at top of file


from pulpcore.app.models import Task

from pulpcore.tasking.constants import TASKING_CONSTANTS
from pulpcore.tasking.services.storage import WorkerDirectory
from pulpcore.tasking.services.worker_watcher import (
    check_worker_processes,
    handle_worker_heartbeat,
    mark_worker_offline
)


_logger = logging.getLogger(__name__)


class PulpWorker(Worker):
    """
    A Pulp worker for both the resource manager and generic workers

    This worker is customized in the following ways:

        * Replaces the string '%h' in the worker name with the fqdn
        * If the name starts with 'reserved_resource_worker' the worker ignores any other Queue
          configuration and only subscribes to a queue of the same name as the worker name
        * If the name starts with 'resource_manager' the worker ignores any other Queue
          configuration and only subscribes to the 'resource_manager' queue
        * Sets the worker TTL
        * Supports the killing of a job that is already running
        * Closes the database connection before forking so it is not process shared
    """

    # Do not print "Result is kept for XXX seconds" after each job
    log_result_lifespan = False

    def __init__(self, queues, **kwargs):

        kwargs['name'] = kwargs['name'].replace('%h', socket.getfqdn())

        if kwargs['name'].startswith(TASKING_CONSTANTS.WORKER_PREFIX):
            queues = [Queue(kwargs['name'], connection=kwargs['connection'])]
        if kwargs['name'].startswith(TASKING_CONSTANTS.RESOURCE_MANAGER_WORKER_NAME):
            queues = [Queue('resource_manager', connection=kwargs['connection'])]

        kwargs['default_worker_ttl'] = TASKING_CONSTANTS.WORKER_TTL
        kwargs['job_monitoring_interval'] = TASKING_CONSTANTS.JOB_MONITORING_INTERVAL

        return super().__init__(queues, **kwargs)

    def execute_job(self, *args, **kwargs):
        """
        Close the database connection before forking, so that it is not shared
        """
        django.db.connections.close_all()
        super().execute_job(*args, **kwargs)

    def perform_job(self, job, queue):
        """
        Set the :class:`pulpcore.app.models.Task` to running and install a kill monitor Thread

        This method is called by the worker's work horse thread (the forked child) just before the
        task begins executing. It creates a Thread which monitors a special Redis key which if
        created should kill the task with SIGKILL.

        Args:
            job (rq.job.Job): The job to perform
            queue (rq.queue.Queue): The Queue associated with the job
        """
        try:
            task = Task.objects.get(job_id=job.get_id())
        except Task.DoesNotExist:
            pass
        else:
            task.set_running()

        def check_kill(conn, id, interval=1):
            while True:
                res = conn.srem(TASKING_CONSTANTS.KILL_KEY, id)
                if res > 0:
                    os.kill(os.getpid(), signal.SIGKILL)
                time.sleep(interval)

        t = threading.Thread(target=check_kill, args=(self.connection, job.get_id()))
        t.start()

        return super().perform_job(job, queue)

    def handle_job_failure(self, job, **kwargs):
        """
        Set the :class:`pulpcore.app.models.Task` to failed and record the exception.

        This method is called by rq to handle a job failure.

        Args:
            job (rq.job.Job): The job that experienced the failure
            kwargs (dict): Unused parameters
        """
        try:
            task = Task.objects.get(job_id=job.get_id())
        except Task.DoesNotExist:
            pass
        else:
            exc_type, exc, tb = sys.exc_info()
            task.set_failed(exc, tb)

        return super().handle_job_failure(job, **kwargs)

    def handle_job_success(self, job, queue, started_job_registry):
        """
        Set the :class:`pulpcore.app.models.Task` to completed.

        This method is called by rq to handle a job success.

        Args:
            job (rq.job.Job): The job that experienced the success
            queue (rq.queue.Queue): The Queue associated with the job
            started_job_registry (rq.registry.StartedJobRegistry): The RQ registry of started jobs
        """
        try:
            task = Task.objects.get(job_id=job.get_id())
        except Task.DoesNotExist:
            pass
        else:
            task.set_completed()

        return super().handle_job_success(job, queue, started_job_registry)

    def register_birth(self, *args, **kwargs):
        """
        Handle the birth of a RQ worker.

        This creates the working directory and removes any vestige records from a previous worker
        with the same name.

        Args:
            args (tuple): unused positional arguments
            kwargs (dict): unused keyword arguments
        """
        mark_worker_offline(self.name, normal_shutdown=True)
        working_dir = WorkerDirectory(self.name)
        working_dir.delete()
        working_dir.create()
        return super().register_birth(*args, **kwargs)

    def heartbeat(self, *args, **kwargs):
        """
        Handle the heartbeat of a RQ worker.

        This writes the heartbeat records to the :class:`pulpcore.app.models.Worker` records.

        Args:
            args (tuple): unused positional arguments
            kwargs (dict): unused keyword arguments
        """
        handle_worker_heartbeat(self.name)
        check_worker_processes()
        return super().heartbeat(*args, **kwargs)

    def handle_warm_shutdown_request(self, *args, **kwargs):
        """
        Handle the warm shutdown of a RQ worker.

        This cleans up any leftover records and marks the :class:`pulpcore.app.models.Worker`
        record as being a clean shutdown.

        Args:
            args (tuple): unused positional arguments
            kwargs (dict): unused keyword arguments
        """
        mark_worker_offline(self.name, normal_shutdown=True)
        return super().handle_warm_shutdown_request(*args, **kwargs)
