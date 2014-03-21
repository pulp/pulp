# -*- coding: utf-8 -*-
#
# Copyright © 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import logging

import celery

from pulp.common.error_codes import PLP0002, PLP0003, PLP0007
from pulp.common.tags import action_tag, resource_tag, RESOURCE_REPOSITORY_TYPE
from pulp.server.async.tasks import Task, TaskResult
from pulp.server.exceptions import PulpCodedException
from pulp.server.managers import factory as managers
from pulp.server.managers.repo.publish import publish as publish_task
from pulp.server.tasks import consumer


logger = logging.getLogger(__name__)


@celery.task(base=Task)
def delete(repo_id):
    """
    Get the itinerary for deleting a repository.
      1. Delete the repository on the sever.
      2. Unbind any bound consumers.
    :param repo_id: A repository ID.
    :type repo_id: str
    :return: A TaskRequest object with the details of any errors or spawned tasks
    :rtype TaskRequest
    """
    # delete repository
    manager = managers.repo_manager()
    manager.delete_repo(repo_id)

    # append unbind itineraries foreach bound consumer
    options = {}
    manager = managers.consumer_bind_manager()

    additional_tasks = []
    errors = []
    for bind in manager.find_by_repo(repo_id):
        try:
            report = consumer.unbind(bind['consumer_id'],
                                     bind['repo_id'],
                                     bind['distributor_id'],
                                     options)
            if report:
                additional_tasks.extend(report.spawned_tasks)
        except Exception, e:
            errors.append(e)

    error = None
    if len(errors) > 0:
        error = PulpCodedException(PLP0007, repo_id=repo_id)
        error.child_exceptions = errors

    return TaskResult(error=error, spawned_tasks=additional_tasks)


@celery.task(base=Task)
def distributor_delete(repo_id, distributor_id):
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
    # delete distributor

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


@celery.task(base=Task)
def distributor_update(repo_id, distributor_id, config, delta):
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

    # update the distributor
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


@celery.task(base=Task)
def publish(repo_id, distributor_id, overrides=None):
    """
    Create an itinerary for repo publish.
    :param repo_id: id of the repo to publish
    :type repo_id: str
    :param distributor_id: id of the distributor to use for the repo publish
    :type distributor_id: str
    :param overrides: dictionary of options to pass to the publish manager
    :type overrides: dict or None
    :return: list of call requests
    :rtype: list
    """
    kwargs = {
        'repo_id': repo_id,
        'distributor_id': distributor_id,
        'publish_config_override': overrides
    }

    tags = [resource_tag(RESOURCE_REPOSITORY_TYPE, repo_id),
            action_tag('publish')]

    return publish_task.apply_async_with_reservation(
        RESOURCE_REPOSITORY_TYPE, repo_id, tags=tags, kwargs=kwargs)


@celery.task(base=Task)
def sync_with_auto_publish(repo_id, overrides=None):
    """
    Sync a repository and upon successful completion, publish
    any distributors that are configured for auto publish.

    :param repo_id: id of the repository to create a sync call request list for
    :type repo_id: str
    :param overrides: dictionary of configuration overrides for this sync
    :type overrides: dict or None
    :return: A task result containing the details of the task executed and any spawned tasks
    :rtype: TaskResult
    """
    sync_result = managers.repo_sync_manager().sync(repo_id, sync_config_override=overrides)

    result = TaskResult(sync_result)

    repo_publish_manager = managers.repo_publish_manager()
    auto_distributors = repo_publish_manager.auto_distributors(repo_id)

    spawned_tasks = []
    for distributor in auto_distributors:
        distributor_id = distributor['id']
        spawned_tasks.append(publish(repo_id, distributor_id))

    result.spawned_tasks = spawned_tasks

    return result
