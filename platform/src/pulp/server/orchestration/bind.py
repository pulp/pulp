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


def bind_call_requests(consumer_id, repo_id, distributor_id, options):

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
    call_request = CallRequest(
        manager.bind,
        args,
        resources=resources,
        weight=0)
    call_requests.append(call_request)

    # notify agent

    args = [
        consumer_id,
        repo_id,
        distributor_id,
        options
    ]

    manager = managers.consumer_agent_manager()
    call_request = CallRequest(
        manager.bind,
        args,
        weight=0,
        asynchronous=True,
        archive=True)

    def on_succeeded(call_request, call_report):
        manager = managers.consumer_bind_manager()
        manager.request_succeeded(
            consumer_id,
            repo_id,
            distributor_id,
            call_report.task_id)

    def on_failed(call_request, call_report):
        manager = managers.consumer_bind_manager()
        manager.request_failed(
            consumer_id,
            repo_id,
            distributor_id,
            call_report.task_id)

    call_request.add_life_cycle_callback(
        dispatch_constants.CALL_SUCCESS_LIFE_CYCLE_CALLBACK,
        on_succeeded)

    call_request.add_life_cycle_callback(
        dispatch_constants.CALL_FAILURE_LIFE_CYCLE_CALLBACK,
        on_failed)

    call_requests.append(call_request)

    # set dependencies
    call_requests[1].depends_on(call_requests[0])

    return call_requests


def unbind_call_requests(consumer_id, repo_id, distributor_id, options):

    call_requests = []

    # unbind

    manager = managers.consumer_bind_manager()
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
        distributor_id
    ]
    tags = [
        resource_tag(dispatch_constants.RESOURCE_CONSUMER_TYPE, consumer_id),
        resource_tag(dispatch_constants.RESOURCE_REPOSITORY_TYPE, repo_id),
        resource_tag(dispatch_constants.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
        action_tag('unbind')
    ]
    call_request = CallRequest(
        manager.unbind,
        args=args,
        resources=resources,
        tags=tags)
    call_requests.append(call_request)

    # notify agent

    args = [
        consumer_id,
        repo_id,
        distributor_id,
        options,
    ]
    manager = managers.consumer_agent_manager()
    call_request = CallRequest(
        manager.unbind,
        args,
        weight=0,
        asynchronous=True,
        archive=True)

    def on_succeeded(call_request, call_report):
        manager = managers.consumer_bind_manager()
        manager.request_succeeded(
            consumer_id,
            repo_id,
            distributor_id,
            call_report.task_id)

    def on_failed(call_request, call_report):
        manager = managers.consumer_bind_manager()
        manager.request_failed(
            consumer_id,
            repo_id,
            distributor_id,
            call_report.task_id)

    call_request.add_life_cycle_callback(
        dispatch_constants.CALL_SUCCESS_LIFE_CYCLE_CALLBACK,
        on_succeeded)

    call_request.add_life_cycle_callback(
        dispatch_constants.CALL_FAILURE_LIFE_CYCLE_CALLBACK,
        on_failed)

    call_requests.append(call_request)

    # set dependencies
    call_requests[1].depends_on(call_requests[0])

    return call_requests
