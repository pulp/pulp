import logging

import celery

from pulp.common.error_codes import PLP0002, PLP0003
from pulp.server.async.tasks import Task, TaskResult
from pulp.server.controllers import consumer
from pulp.server.exceptions import PulpCodedException
from pulp.server.managers import factory as managers


logger = logging.getLogger(__name__)


@celery.task(base=Task, name='pulp.server.tasks.repository.distributor_delete')
def delete(repo_id, distributor_id):
    """
    Get the itinerary for deleting a repository distributor.
      1. Delete the distributor on the sever.
      2. Unbind any bound consumers.
    :param repo_id: A repository ID.
    :type repo_id: str
    :param distributor_id: A distributor id
    :type distributor_id: str
    :return: Any errors that may have occurred and the list of tasks spawned for each consumer
    :rtype TaskResult
    """
    manager = managers.repo_distributor_manager()
    manager.remove_distributor(repo_id, distributor_id)

    # append unbind itineraries foreach bound consumer

    unbind_errors = []
    additional_tasks = []
    options = {}
    manager = managers.consumer_bind_manager()
    for bind in manager.find_by_distributor(repo_id, distributor_id):
        try:
            report = consumer.unbind(bind['consumer_id'],
                                     bind['repo_id'],
                                     bind['distributor_id'],
                                     options)
            if report:
                additional_tasks.extend(report.spawned_tasks)
        except Exception, e:
            unbind_errors.append(e)

    bind_error = None
    if len(unbind_errors) > 0:
        bind_error = PulpCodedException(PLP0003, repo_id=repo_id, distributor_id=distributor_id)
        bind_error.child_exceptions = unbind_errors
    return TaskResult(error=bind_error, spawned_tasks=additional_tasks)


@celery.task(base=Task, name='pulp.server.tasks.repository.distributor_update')
def update(repo_id, distributor_id, config, delta):
    """
    Get the itinerary for updating a repository distributor.
      1. Update the distributor on the server.
      2. (re)bind any bound consumers.

    :param repo_id:         A repository ID.
    :type  repo_id:         str
    :param distributor_id:  A unique distributor id
    :type  distributor_id:  str
    :param config:          A configuration dictionary for a distributor instance. The contents of
                            this dict depends on the type of distributor.
    :type  config:          dict
    :param delta:           A dictionary used to change other saved configuration values for a
                            distributor instance. This currently only supports the 'auto_publish'
                            keyword, which should have a value of type bool
    :type  delta:           dict or None

    :return: Any errors that may have occurred and the list of tasks spawned for each consumer
    :rtype: TaskResult
    """
    manager = managers.repo_distributor_manager()

    # Retrieve configuration options from the delta
    auto_publish = None
    if delta is not None:
        auto_publish = delta.get('auto_publish')

    distributor = manager.update_distributor_config(repo_id, distributor_id, config, auto_publish)

    # Process each bound consumer
    bind_errors = []
    additional_tasks = []
    options = {}
    manager = managers.consumer_bind_manager()

    for bind in manager.find_by_distributor(repo_id, distributor_id):
        try:
            report = consumer.bind(bind['consumer_id'],
                                   bind['repo_id'],
                                   bind['distributor_id'],
                                   bind['notify_agent'],
                                   bind['binding_config'],
                                   options)
            if report.spawned_tasks:
                additional_tasks.extend(report.spawned_tasks)
        except Exception, e:
            bind_errors.append(e)

    bind_error = None
    if len(bind_errors) > 0:
        bind_error = PulpCodedException(PLP0002, repo_id=repo_id, distributor_id=distributor_id)
        bind_error.child_exceptions = bind_errors
    return TaskResult(distributor, bind_error, additional_tasks)
