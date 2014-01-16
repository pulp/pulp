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

from pulp.common.tags import (action_tag, resource_tag, ACTION_AGENT_BIND, ACTION_AGENT_UNBIND)
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch.call import CallReport
from pulp.server.managers import factory as managers


@celery.task
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

    :returns CallReport for additional calls that need to be executed or None if no calls
    :rtype: CallReport

    :raises pulp.server.exceptions.MissingResource: when given consumer does not exist
    """
    response = None
    # Create the binding on the server
    bind_manager = managers.consumer_bind_manager()
    bind_manager.bind(consumer_id, repo_id, distributor_id, notify_agent, binding_config)

    # Notify the agents of the binding - return a 202 with the list of task ids
    if notify_agent:
        agent_manager = managers.consumer_agent_manager()
        task_id = agent_manager.bind(consumer_id, repo_id, distributor_id, agent_options)
        tags = [
            resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id),
            resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
            resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
            action_tag(ACTION_AGENT_BIND)
        ]
        response = CallReport(call_request_id=task_id, call_request_tags=tags)

    return response


@celery.task
def unbind(consumer_id, repo_id, distributor_id, options):
    """
    Unbinda  consumer.

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
    :return: A list of call_requests
    :rtype list
    :raises pulp.server.exceptions.MissingResource: when given consumer does not exist
    """
    response = None

    bind_manager = managers.consumer_bind_manager()
    binding = bind_manager.get_bind(consumer_id, repo_id, distributor_id)

    if binding['notify_agent']:
        # The agent notification handler will delete the binding from the server
        tags = [
            resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id),
            resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
            resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
            action_tag(ACTION_AGENT_UNBIND)
        ]
        agent_manager = managers.consumer_agent_manager()

        task_id = agent_manager.unbind(consumer_id, repo_id, distributor_id, options)
        response = CallReport(call_request_id=task_id, call_request_tags=tags)
    else:
        # Since there was no agent notification, perform the delete immediately
        bind_manager.delete(consumer_id, repo_id, distributor_id, True)

    return response


@celery.task
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
    @param consumer_id: A consumer ID.
    @type consumer_id: str
    @param repo_id: A repository ID.
    @type repo_id: str
    @param distributor_id: A distributor ID.
    @type distributor_id: str
    @param options: Unbind options passed to the agent handler.
    @type options: dict
    @return: A list of call_requests
    @rtype list
    """
    response = None

    bind_manager = managers.consumer_bind_manager()
    binding = bind_manager.get_bind(consumer_id, repo_id, distributor_id)
    bind_manager.delete(consumer_id, repo_id, distributor_id, True)

    if binding['notify_agent']:
        tags = [
            resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id),
            resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
            resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
            action_tag(ACTION_AGENT_UNBIND)
        ]
        agent_manager = managers.consumer_agent_manager()

        task_id = agent_manager.unbind(consumer_id, repo_id, distributor_id, options)
        response = CallReport(call_request_id=task_id, call_request_tags=tags)

    return response


@celery.task
def install_content(consumer_id, units, options):
    pass


@celery.task
def update_content(consumer_id, units, options):
    pass


@celery.task
def uninstall_content(consumer_id, units, options):
    pass
