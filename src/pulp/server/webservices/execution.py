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

from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.dispatch.exceptions import CallRejectedException
from pulp.server.webservices import serialization

# execution wrapper api --------------------------------------------------------

def execute(controller, call_request, expexted_response='ok'):
    coordinator = dispatch_factory.coordinator()
    return _execute_single(controller,
                           coordinator.execute_call,
                           call_request,
                           expexted_response)


def execute_async(controller, call_request, expexted_response='ok'):
    coordinator = dispatch_factory.coordinator()
    return _execute_single(controller,
                           coordinator.execute_call_asynchronously,
                           call_request,
                           expexted_response)


def execute_sync(controller, call_request, expexted_response='ok'):
    coordinator = dispatch_factory.coordinator()
    return _execute_single(controller,
                           coordinator.execute_call_synchronously,
                           call_request,
                           expexted_response)


# execution utilities ----------------------------------------------------------

def _execute_single(controller, execute_method, call_request, expected_response):
    call_report = execute_method(call_request)
    if call_report.response is dispatch_constants.CALL_REJECTED_RESPONSE:
        raise CallRejectedException(call_report.serialize)
    if call_report.response is dispatch_constants.CALL_POSTPONED_RESPONSE or \
       call_report.state in dispatch_constants.CALL_INCOMPLETE_STATES:
        serialized_call_report = call_report.serialize()
        link = serialization.dispatch.task_href(call_report)
        serialized_call_report.update(link)
        return controller.accepted(serialized_call_report)
    if call_report.state is dispatch_constants.CALL_ERROR_STATE:
        raise call_report.exception, None, call_report.traceback
    # only remaining states are 'cancelled' and 'finished';
    # I don't believe we can get 'cancelled' here
    response_method = getattr(controller, expected_response)
    return expected_response(call_report.result)
