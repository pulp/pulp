# Copyright (c) 2010 Red Hat, Inc.
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

from pulp.server.dispatch.call import CallRequest
from pulp.common.tags import (action_tag, resource_tag, ACTION_BIND, ACTION_AGENT_BIND,
                              ACTION_UNBIND, ACTION_AGENT_UNBIND, ACTION_DELETE_BINDING)
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.managers import factory as managers


logger = logging.getLogger(__name__)


def bind_succeeded(call_request, call_report):
    """
    The task succeeded callback.
    Updates the consumer request tracking on the binding.
    """
    manager = managers.consumer_bind_manager()
    action_id = call_request.id
    consumer_id, repo_id, distributor_id, options = call_request.args
    dispatch_report = call_report.result
    if dispatch_report['succeeded']:
        manager.action_succeeded(consumer_id, repo_id, distributor_id, action_id)
    else:
        manager.action_failed(consumer_id, repo_id, distributor_id, action_id)


def bind_failed(call_request, call_report):
    """
    The task failed callback.
    Updates the consumer request tracking on the binding.
    """
    manager = managers.consumer_bind_manager()
    action_id = call_request.id
    consumer_id, repo_id, distributor_id, options = call_request.args
    manager.action_failed(consumer_id, repo_id, distributor_id, action_id)


# just mapped to bind functions because the behavior is the same
# but want to use these names in the unbind itinerary for clarity.
unbind_succeeded = bind_succeeded
unbind_failed = bind_failed


def bind_itinerary(consumer_id, repo_id, distributor_id, notify_agent, binding_config, agent_options):
    """
    Get the bind itinerary:
      1. Create the binding on the server.
      2. Request that the consumer (agent) perform the bind.
    @param consumer_id: A consumer ID.
    @type consumer_id: str
    @param repo_id: A repository ID.
    @type repo_id: str
    @param distributor_id: A distributor ID.
    @type distributor_id: str
    @param agent_options: Bind options passed to the agent handler.
    @type agent_options: dict
    @param notify_agent: indicates if the agent should be sent a message about the new binding
    @type  notify_agent: bool
    @param binding_config: configuration options to use when generating the payload for this binding

    @return: A list of call_requests.
    @rtype list
    """

    call_requests = []
    bind_manager = managers.consumer_bind_manager()
    agent_manager = managers.consumer_agent_manager()

    # bind

    tags = [
        resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id),
        resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
        resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
        action_tag(ACTION_BIND)
    ]

    args = [
        consumer_id,
        repo_id,
        distributor_id,
        notify_agent,
        binding_config,
    ]

    bind_request = CallRequest( # rbarlow_converted
        bind_manager.bind,
        args,
        weight=0,
        tags=tags)

    bind_request.reads_resource(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id)
    bind_request.reads_resource(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id)
    bind_request.reads_resource(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id)

    call_requests.append(bind_request)

    # notify agent

    if notify_agent:
        tags = [
            resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id),
            resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
            resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
            action_tag(ACTION_AGENT_BIND)
        ]

        args = [
            consumer_id,
            repo_id,
            distributor_id,
            agent_options
        ]

        agent_request = CallRequest( # rbarlow_converted
            agent_manager.bind,
            args,
            weight=0,
            asynchronous=True,
            archive=True,
            tags=tags)

        agent_request.add_life_cycle_callback(
            dispatch_constants.CALL_SUCCESS_LIFE_CYCLE_CALLBACK,
            bind_succeeded)

        agent_request.add_life_cycle_callback(
            dispatch_constants.CALL_FAILURE_LIFE_CYCLE_CALLBACK,
            bind_failed)

        call_requests.append(agent_request)

        agent_request.depends_on(bind_request.id)

    return call_requests


def unbind_itinerary(consumer_id, repo_id, distributor_id, options):
    """
    Get the unbind itinerary.
    The tasks in the itinerary are as follows:
      1. Mark the binding as (deleted) on the server.
      2. Request that the consumer (agent) perform the unbind.
      3. Delete the binding on the server.
    @param consumer_id: A consumer ID.
    @type consumer_id: str
    @param repo_id: A repository ID.
    @type repo_id: str
    @param distributor_id: A distributor ID.
    @type distributor_id: str
    @param options: Unbind options passed to the agent handler.
    @type options: dict
    @return: A list of call_requests.
    @rtype list
    """

    call_requests = []
    bind_manager = managers.consumer_bind_manager()
    binding = bind_manager.get_bind(consumer_id, repo_id, distributor_id)

    # agent not participating in the bind/unbind - always want a forced unbind.
    if not binding['notify_agent']:
        return forced_unbind_itinerary(consumer_id, repo_id, distributor_id, options)

    # unbind

    tags = [
        resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id),
        resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
        resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
        action_tag(ACTION_UNBIND)
    ]

    args = [
        consumer_id,
        repo_id,
        distributor_id,
    ]

    unbind_request = CallRequest( # rbarlow_converted
        bind_manager.unbind,
        args=args,
        tags=tags)
    unbind_request.reads_resource(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id)
    call_requests.append(unbind_request)

    # notify agent

    tags = [
        resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id),
        resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
        resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
        action_tag(ACTION_AGENT_UNBIND)
    ]

    args = [
        consumer_id,
        repo_id,
        distributor_id,
        options,
    ]

    agent_manager = managers.consumer_agent_manager()

    agent_request = CallRequest( # rbarlow_converted
        agent_manager.unbind,
        args,
        weight=0,
        asynchronous=True,
        archive=True,
        tags=tags)

    agent_request.add_life_cycle_callback(
        dispatch_constants.CALL_SUCCESS_LIFE_CYCLE_CALLBACK,
        unbind_succeeded)

    agent_request.add_life_cycle_callback(
        dispatch_constants.CALL_FAILURE_LIFE_CYCLE_CALLBACK,
        unbind_failed)

    call_requests.append(agent_request)

    agent_request.depends_on(unbind_request.id)

    # delete the binding

    tags = [
        resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id),
        resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
        resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
        action_tag(ACTION_DELETE_BINDING)
    ]

    args = [
        consumer_id,
        repo_id,
        distributor_id
    ]

    delete_request = CallRequest(bind_manager.delete, args=args, tags=tags) # rbarlow_converted
    unbind_request.reads_resource(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id)
    call_requests.append(delete_request)
    delete_request.depends_on(agent_request.id)

    return call_requests


def forced_unbind_itinerary(consumer_id, repo_id, distributor_id, options):
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

    call_requests = []
    bind_manager = managers.consumer_bind_manager()
    binding = bind_manager.get_bind(consumer_id, repo_id, distributor_id)

    # unbind

    tags = [
        resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id),
        resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
        resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
        action_tag(ACTION_UNBIND)
    ]

    args = [
        consumer_id,
        repo_id,
        distributor_id,
        True,
    ]

    delete_request = CallRequest(bind_manager.delete, args=args, tags=tags) # rbarlow_converted
    delete_request.reads_resource(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id)
    call_requests.append(delete_request)

    # notify agent conditionally

    if binding['notify_agent']:

        tags = [
            resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id),
            resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
            resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
            action_tag(ACTION_AGENT_UNBIND)
        ]

        args = [
            consumer_id,
            repo_id,
            distributor_id,
            options,
        ]

        agent_manager = managers.consumer_agent_manager()

        agent_request = CallRequest( # rbarlow_converted
            agent_manager.unbind,
            args,
            weight=0,
            asynchronous=True,
            archive=True,
            tags=tags)

        call_requests.append(agent_request)
        agent_request.depends_on(delete_request.id)

    return call_requests
