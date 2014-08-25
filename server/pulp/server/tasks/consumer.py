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

import celery

from pulp.server.async.tasks import TaskResult, Task
from pulp.server.managers import factory as managers


def bind(consumer_id, repo_id, distributor_id, notify_agent, binding_config, agent_options):
    """
    Bind a repo to a consumer:
      1. Create the binding on the server.
      2. Request that the consumer (agent) perform the bind.
    :param consumer_id: A consumer ID.
    :type consumer_id: str
    :param repo_id: A repository ID.
    :type repo_id: str
    :param distributor_id: A distributor ID.
    :type distributor_id: str
    :param agent_options: Bind options passed to the agent handler.
    :type agent_options: dict
    :param notify_agent: indicates if the agent should be sent a message about the new binding
    :type  notify_agent: bool
    :param binding_config: configuration options to use when generating the payload for this binding

    :returns TaskResult containing the result of the bind & any spawned tasks or a dictionary
             of the bind result if no tasks were spawned.
    :rtype: TaskResult

    :raises pulp.server.exceptions.MissingResource: when given consumer does not exist
    """
    # Create the binding on the server
    bind_manager = managers.consumer_bind_manager()
    binding = bind_manager.bind(consumer_id, repo_id, distributor_id, notify_agent, binding_config)

    response = TaskResult(result=binding)

    # Notify the agents of the binding
    if notify_agent:
        agent_manager = managers.consumer_agent_manager()
        task = agent_manager.bind(consumer_id, repo_id, distributor_id, agent_options)
        # we only want the task's ID, not the full task
        response.spawned_tasks.append({'task_id': task.get('task_id')})

    return response


def unbind(consumer_id, repo_id, distributor_id, options):
    """
    Unbind a  consumer.
    The itinerary is:
      1. Unbind the consumer from the repo on the server (mark the binding on the server as deleted).
      2. Request that the consumer (agent) perform the unbind.
      3. Delete the binding on the server.

    :param consumer_id: A consumer ID.
    :type consumer_id: str
    :param repo_id: A repository ID.
    :type repo_id: str
    :param distributor_id: A distributor ID.
    :type distributor_id: str
    :param options: Unbind options passed to the agent handler.
    :type options: dict
    :returns TaskResult containing the result of the unbind & any spawned tasks or a dictionary
             of the unbind result if no tasks were spawned.
    :rtype: TaskResult
    """

    bind_manager = managers.consumer_bind_manager()
    binding = bind_manager.get_bind(consumer_id, repo_id, distributor_id)

    response = TaskResult(result=binding)

    if binding['notify_agent']:
        # Unbind the consumer from the repo on the server
        bind_manager.unbind(consumer_id, repo_id, distributor_id)
        # Notify the agent to remove the binding.
        # The agent notification handler will delete the binding from the server
        agent_manager = managers.consumer_agent_manager()
        task = agent_manager.unbind(consumer_id, repo_id, distributor_id, options)
        # we only want the task's ID, not the full task
        response.spawned_tasks.append({'task_id': task.get('task_id')})
    else:
        # Since there was no agent notification, perform the delete immediately
        bind_manager.delete(consumer_id, repo_id, distributor_id, True)

    return response


def force_unbind(consumer_id, repo_id, distributor_id, options):
    """
    Get the unbind itinerary.
    A forced unbind immediately deletes the binding instead
    of marking it deleted and going through that lifecycle.
    It is intended to be used to clean up orphaned bindings
    caused by failed/unconfirmed unbind actions on the consumer.
    The itinerary is:
      1. Delete the binding on the server.
      2. Request that the consumer (agent) perform the unbind.
    :param consumer_id: A consumer ID.
    :type consumer_id: str
    :param repo_id: A repository ID.
    :type repo_id: str
    :param distributor_id: A distributor ID.
    :type distributor_id: str
    :param options: Unbind options passed to the agent handler.
    :type options: dict
    :returns TaskResult containing the result of the unbind & any spawned tasks or a dictionary
             of the unbind result if no tasks were spawned.
    :rtype: TaskResult
    """

    bind_manager = managers.consumer_bind_manager()
    binding = bind_manager.get_bind(consumer_id, repo_id, distributor_id)
    bind_manager.delete(consumer_id, repo_id, distributor_id, True)

    response = TaskResult()

    if binding['notify_agent']:
        agent_manager = managers.consumer_agent_manager()
        task = agent_manager.unbind(consumer_id, repo_id, distributor_id, options)
        # we only want the task's ID, not the full task
        response.spawned_tasks.append({'task_id': task.get('task_id')})

    return response


@celery.task(base=Task)
def install_content(consumer_id, units, options):
    """
    Install units on a consumer

    :param consumer_id: unique id of the consumer
    :type consumer_id: str
    :param units: units to install
    :type units: list or tuple
    :param options: options to pass to the install manager
    :type options: dict or None
    :returns Dictionary representation of a task status
    :rtype: dictionary
    """
    agent_manager = managers.consumer_agent_manager()
    return agent_manager.install_content(consumer_id, units, options)


@celery.task(base=Task)
def update_content(consumer_id, units, options):
    """
    Update units on a consumer.

    :param consumer_id: unique id of the consumer
    :type consumer_id: str
    :param units: units to install
    :type units: list or tuple
    :param options: options to pass to the install manager
    :type options: dict or None
    :returns Dictionary representation of a task status
    :rtype: dictionary
    """
    agent_manager = managers.consumer_agent_manager()
    return agent_manager.update_content(consumer_id, units, options)


@celery.task(base=Task)
def uninstall_content(consumer_id, units, options):
    """
    Uninstall content from a consumer.

    :param consumer_id: unique id of the consumer
    :type consumer_id: str
    :param units: units to install
    :type units: list or tuple
    :param options: options to pass to the install manager
    :type options: dict or None
    :returns Dictionary representation of a task status
    :rtype: dictionary
    """
    agent_manager = managers.consumer_agent_manager()
    return agent_manager.uninstall_content(consumer_id, units, options)
