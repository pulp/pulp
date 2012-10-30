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
from pulp.common.tags import action_tag, resource_tag
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.managers import factory as managers


_LOG = logging.getLogger(__name__)


# -- task callbacks ----------------------------------------------------------------------

def bind_succeeded(call_request, call_report):
    """
    The task succeeded callback.
    Updates the consumer request tracking on the binding.
    @param call_request:
    @param call_report:
    """
    manager = managers.consumer_bind_manager()
    request_id = call_request.id
    consumer_id, repo_id, distributor_id, options = call_request.args
    dispatch_report = call_report.result
    if dispatch_report['status']:
        manager.request_succeeded(consumer_id, repo_id, distributor_id, request_id)
    else:
        manager.request_failed(consumer_id, repo_id, distributor_id, request_id)

def bind_failed(call_request, call_report):
    """
    The task failed callback.
    Updates the consumer request tracking on the binding.
    @param call_request:
    @param call_report:
    """
    manager = managers.consumer_bind_manager()
    request_id = call_request.id
    consumer_id, repo_id, distributor_id, options = call_request.args
    manager.request_failed(consumer_id, repo_id, distributor_id, request_id)

# just mapped to bind functions because the behavior is the same
# but want to use these names in the unbind itinerary for clarity.
unbind_succeeded = bind_succeeded
unbind_failed = bind_failed


# -- itineraries -------------------------------------------------------------------------


def bind_itinerary(consumer_id, repo_id, distributor_id, options):
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
    @param options: Bind options passed to the agent handler.
    @type options: dict
    @return: A list of call_requests known as an itinerary.
    @rtype list
    """

    call_requests = []

    # bind

    resources = {
        dispatch_constants.RESOURCE_CONSUMER_TYPE:
            {consumer_id:dispatch_constants.RESOURCE_READ_OPERATION},
        dispatch_constants.RESOURCE_REPOSITORY_TYPE:
            {repo_id:dispatch_constants.RESOURCE_READ_OPERATION},
        dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE:
            {distributor_id:dispatch_constants.RESOURCE_READ_OPERATION},
    }

    args = [
        consumer_id,
        repo_id,
        distributor_id,
    ]

    manager = managers.consumer_bind_manager()
    bind_request = CallRequest(
        manager.bind,
        args,
        resources=resources,
        weight=0)

    call_requests.append(bind_request)

    # notify agent

    args = [
        consumer_id,
        repo_id,
        distributor_id,
        options
    ]

    manager = managers.consumer_agent_manager()
    agent_request = CallRequest(
        manager.bind,
        args,
        weight=0,
        asynchronous=True,
        archive=True)

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
    Get the unbind itinerary:
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
    @return: A list of call_requests known as an itinerary.
    @rtype list
    """

    call_requests = []

    # unbind

    manager = managers.consumer_bind_manager()
    resources = {
        dispatch_constants.RESOURCE_CONSUMER_TYPE:
            {consumer_id:dispatch_constants.RESOURCE_READ_OPERATION},
        }

    args = [
        consumer_id,
        repo_id,
        distributor_id
        ]

    tags = [
        resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id),
        resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
        resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
        action_tag('unbind')
        ]

    unbind_request = CallRequest(
        manager.unbind,
        args=args,
        resources=resources,
        tags=tags)

    call_requests.append(unbind_request)

    # notify agent

    args = [
        consumer_id,
        repo_id,
        distributor_id,
        options,
        ]

    manager = managers.consumer_agent_manager()
    agent_request = CallRequest(
        manager.unbind,
        args,
        weight=0,
        asynchronous=True,
        archive=True)

    agent_request.add_life_cycle_callback(
        dispatch_constants.CALL_SUCCESS_LIFE_CYCLE_CALLBACK,
        unbind_succeeded)

    agent_request.add_life_cycle_callback(
        dispatch_constants.CALL_FAILURE_LIFE_CYCLE_CALLBACK,
        unbind_failed)

    call_requests.append(agent_request)

    agent_request.depends_on(unbind_request.id)

    # delete the bind

    manager = managers.consumer_bind_manager()
    resources = {
        dispatch_constants.RESOURCE_CONSUMER_TYPE:
            {consumer_id:dispatch_constants.RESOURCE_READ_OPERATION},
        }

    args = [
        consumer_id,
        repo_id,
        distributor_id
        ]

    tags = [
        resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id),
        resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
        resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
        action_tag('delete')
        ]

    delete_request = CallRequest(
        manager.delete,
        args=args,
        resources=resources,
        tags=tags)

    call_requests.append(delete_request)

    delete_request.depends_on(agent_request.id)

    return call_requests
