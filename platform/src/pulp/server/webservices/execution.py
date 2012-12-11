# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from datetime import  timedelta

from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.exceptions import (
    ConflictingOperation, MultipleOperationsPostponed, OperationPostponed)

# execution wrapper api --------------------------------------------------------

def execute(call_request, call_report=None):
    """
    Execute a call request through the controller and return the result iff the
    call was executed immediately.
    @param call_request: call request to execute
    @type  call_request: pulp.server.dispatch.call.CallRequest
    @return: return value from call in call request
    """
    coordinator = dispatch_factory.coordinator()
    call_report = coordinator.execute_call(call_request, call_report)
    if call_report.response is dispatch_constants.CALL_REJECTED_RESPONSE:
        raise ConflictingOperation(call_report.reasons)
    if call_report.state in dispatch_constants.CALL_INCOMPLETE_STATES:
        raise OperationPostponed(call_report)
    if call_report.state is dispatch_constants.CALL_ERROR_STATE:
        raise call_report.exception, None, call_report.traceback
    return call_report.result


def execute_ok(controller, call_request, call_report=None):
    """
    DEPRECATED! This method has been deprecated. Please use 'execute' instead.
                The only change you will need to make is to handle calling ok()
                from within the controller, instead of expecting this method to
                do it for you.

    Execute a call request via the coordinator.
    @param controller: web services rest controller
    @type  controller: pulp.server.webservices.controller.base.JSONController
    @param call_request: call request to execute
    @type  call_request: pulp.server.dispatch.call.CallRequest
    @return: http server response
    """
    return controller.ok(execute(call_request, call_report))


def execute_created(controller, call_request, location):
    """
    Execute a call request via the coordinator.
    @param controller: web services rest controller
    @type  controller: pulp.server.webservices.controller.base.JSONController
    @param call_request: call request to execute
    @type  call_request: pulp.server.dispatch.call.CallRequest
    @param location: the location of the created resource
    @type  location: str
    @return: http server response
    @deprecated: create should always return an _href field which requires post
                 return processing
    """
    coordinator = dispatch_factory.coordinator()
    call_report = coordinator.execute_call(call_request)
    if call_report.response is dispatch_constants.CALL_REJECTED_RESPONSE:
        raise ConflictingOperation(call_report.reasons)
    # covers postponed and accepted
    if call_report.state in dispatch_constants.CALL_INCOMPLETE_STATES:
        raise OperationPostponed(call_report)
    if call_report.state is dispatch_constants.CALL_ERROR_STATE:
        raise call_report.exception, None, call_report.traceback
    return controller.created(location, call_report.result)


def execute_async(controller, call_request, call_report=None):
    """
    Execute a call request asynchronously via the coordinator.
    @param controller: web services rest controller
    @type  controller: pulp.server.webservices.controller.base.JSONController
    @param call_request: call request to execute
    @type  call_request: pulp.server.dispatch.call.CallRequest
    @return: http server response
    """
    coordinator = dispatch_factory.coordinator()
    call_report = coordinator.execute_call_asynchronously(call_request, call_report)
    if call_report.response is dispatch_constants.CALL_REJECTED_RESPONSE:
        raise ConflictingOperation(call_report.reasons)
    raise OperationPostponed(call_report)


def execute_sync(call_request, call_report=None, timeout=timedelta(seconds=20)):
    """
    Execute a call request synchronously via the coordinator.
    @param call_request: call request to execute
    @type  call_request: pulp.server.dispatch.call.CallRequest
    @param timeout: time to wait for task to start before raising and exception
    @type  timeout: datetime.timedelta
    @return: return value from call in call request
    """
    coordinator = dispatch_factory.coordinator()
    call_report = coordinator.execute_call_synchronously(call_request, call_report, timeout)
    if call_report.response is dispatch_constants.CALL_REJECTED_RESPONSE:
        raise ConflictingOperation(call_report.reasons)
    if call_report.state is dispatch_constants.CALL_ERROR_STATE:
        raise call_report.exception, None, call_report.traceback
    return call_report.result


def execute_sync_ok(controller, call_request, timeout=timedelta(seconds=20)):
    """
    Execute a call request synchronously via the coordinator.
    @param controller: web services rest controller
    @type  controller: pulp.server.webservices.controller.base.JSONController
    @param call_request: call request to execute
    @type  call_request: pulp.server.dispatch.call.CallRequest
    @param timeout: time to wait for task to start before raising and exception
    @type  timeout: datetime.timedelta
    @return: http server response
    """
    coordinator = dispatch_factory.coordinator()
    call_report = coordinator.execute_call_synchronously(call_request, timeout=timeout)
    if call_report.response is dispatch_constants.CALL_REJECTED_RESPONSE:
        raise ConflictingOperation(call_report.reasons)
    if call_report.state is dispatch_constants.CALL_ERROR_STATE:
        raise call_report.exception, None, call_report.traceback
    return controller.ok(call_report.result)


def execute_sync_created(controller, call_request, location, timeout=timedelta(seconds=20)):
    """
    Execute a call request synchronously via the coordinator.
    @param controller: web services rest controller
    @type  controller: pulp.server.webservices.controller.base.JSONController
    @param call_request: call request to execute
    @type  call_request: pulp.server.dispatch.call.CallRequest
    @param location: the location of the created resource
    @type  location: str
    @param timeout: time to wait for task to start before raising and exception
    @type  timeout: datetime.timedelta
    @return: http server response
    """
    coordinator = dispatch_factory.coordinator()
    call_report = coordinator.execute_call_synchronously(call_request, timeout=timeout)
    if call_report.response is dispatch_constants.CALL_REJECTED_RESPONSE:
        raise ConflictingOperation(call_report.reasons)
    if call_report.state is dispatch_constants.CALL_ERROR_STATE:
        raise call_report.exception, None, call_report.traceback
    return controller.created(location, call_report.result)


def execute_multiple(call_request_list):
    """
    Execute multiple calls as a task group via the coordinator.
    @param call_request_list: list of call request instances
    @type call_request_list: list
    """
    coordinator = dispatch_factory.coordinator()
    call_report_list = coordinator.execute_multiple_calls(call_request_list)
    if call_report_list[0].response is dispatch_constants.CALL_REJECTED_RESPONSE:
        # the coordinator will put the reasons on the call report that conflicted
        reasons = reduce(lambda p, c: c.reasons or p, call_report_list, None)
        raise ConflictingOperation(reasons)
    raise MultipleOperationsPostponed(call_report_list)

