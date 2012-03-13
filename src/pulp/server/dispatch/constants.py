# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# execution hooks --------------------------------------------------------------

CALL_ENQUEUE_EXECUTION_HOOK = 0
CALL_DEQUEUE_EXECUTION_HOOK = 1
CALL_RUN_EXECUTION_HOOK = 2
CALL_SUCCESS_EXECUTION_HOOK = 3
CALL_FAILURE_EXECUTION_HOOK = 4
CALL_CANCEL_EXECUTION_HOOK = 5
CALL_COMPLETE_EXECUTION_HOOK = 6

CALL_EXECUTION_HOOKS = (CALL_ENQUEUE_EXECUTION_HOOK,
                        CALL_DEQUEUE_EXECUTION_HOOK,
                        CALL_RUN_EXECUTION_HOOK,
                        CALL_SUCCESS_EXECUTION_HOOK,
                        CALL_FAILURE_EXECUTION_HOOK,
                        CALL_CANCEL_EXECUTION_HOOK,
                        CALL_COMPLETE_EXECUTION_HOOK)


_CALL_EXECUTION_HOOK_STRINGS = (
    'enqueue',
    'dequeue',
    'run',
    'success',
    'failure',
    'cancel',
    'complete'
)

def call_execution_hook_to_string(hook_number):
    assert isinstance(hook_number, int)
    assert hook_number >= 0 and hook_number < len(_CALL_EXECUTION_HOOK_STRINGS)
    return _CALL_EXECUTION_HOOK_STRINGS[hook_number]

# control hooks ----------------------------------------------------------------

CALL_CANCEL_CONTROL_HOOK = 0

CALL_CONTROL_HOOKS = (CALL_CANCEL_CONTROL_HOOK,)


_CALL_CONTROL_HOOK_STRINGS = (
    'cancel',
)

def call_control_hook_to_string(hook_number):
    assert isinstance(hook_number, int)
    assert hook_number >= 0 and hook_number < len(_CALL_CONTROL_HOOK_STRINGS)
    return _CALL_CONTROL_HOOK_STRINGS[hook_number]

# execution responses ----------------------------------------------------------

CALL_ACCEPTED_RESPONSE = 'accepted'
CALL_POSTPONED_RESPONSE = 'postponed'
CALL_REJECTED_RESPONSE = 'rejected'

CALL_RESPONSES = (CALL_ACCEPTED_RESPONSE,
                  CALL_POSTPONED_RESPONSE,
                  CALL_REJECTED_RESPONSE)

# call states ------------------------------------------------------------------

CALL_WAITING_STATE = 'waiting'
CALL_RUNNING_STATE = 'running'
CALL_SUSPENDED_STATE = 'suspended'
CALL_FINISHED_STATE = 'finished'
CALL_ERROR_STATE = 'error'
CALL_CANCELED_STATE = 'canceled'

CALL_STATES = (CALL_WAITING_STATE,
               CALL_RUNNING_STATE,
               CALL_SUSPENDED_STATE,
               CALL_FINISHED_STATE,
               CALL_ERROR_STATE,
               CALL_CANCELED_STATE)

CALL_READY_STATES = (CALL_WAITING_STATE,)
CALL_INCOMPLETE_STATES = (CALL_WAITING_STATE, CALL_RUNNING_STATE, CALL_SUSPENDED_STATE)
CALL_COMPLETE_STATES = (CALL_FINISHED_STATE, CALL_ERROR_STATE, CALL_CANCELED_STATE)

# resource types ---------------------------------------------------------------

RESOURCE_CDS_TYPE = 'cds'
RESOURCE_CONSUMER_TYPE = 'consumer'
RESOURCE_CONTENT_UNIT_TYPE = 'content unit'
RESOURCE_REPOSITORY_TYPE = 'repository'
RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE = 'repository distributor'
RESOURCE_REPOSITORY_IMPORTER_TYPE = 'repository importer'
RESOURCE_ROLE_TYPE = 'role'
RESOURCE_USER_TYPE = 'user'

RESOURCE_TYPES = (RESOURCE_CDS_TYPE,
                  RESOURCE_CONSUMER_TYPE,
                  RESOURCE_CONTENT_UNIT_TYPE,
                  RESOURCE_REPOSITORY_TYPE,
                  RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE,
                  RESOURCE_REPOSITORY_IMPORTER_TYPE,
                  RESOURCE_ROLE_TYPE,
                  RESOURCE_USER_TYPE)

# resource operations  ---------------------------------------------------------

RESOURCE_CREATE_OPERATION = 'create'
RESOURCE_READ_OPERATION = 'read'
RESOURCE_UPDATE_OPERATION = 'update'
RESOURCE_DELETE_OPERATION = 'delete'

RESOURCE_OPERATIONS = (RESOURCE_CREATE_OPERATION,
                       RESOURCE_READ_OPERATION,
                       RESOURCE_UPDATE_OPERATION,
                       RESOURCE_DELETE_OPERATION)

RESOURCE_OPERATIONS_MATRIX = {
    RESOURCE_CREATE_OPERATION: {RESOURCE_CREATE_OPERATION: CALL_REJECTED_RESPONSE,
                                RESOURCE_READ_OPERATION:   CALL_POSTPONED_RESPONSE,
                                RESOURCE_UPDATE_OPERATION: CALL_POSTPONED_RESPONSE,
                                RESOURCE_DELETE_OPERATION: CALL_POSTPONED_RESPONSE},
    RESOURCE_READ_OPERATION:   {RESOURCE_CREATE_OPERATION: CALL_POSTPONED_RESPONSE,
                                RESOURCE_READ_OPERATION:   CALL_ACCEPTED_RESPONSE,
                                RESOURCE_UPDATE_OPERATION: CALL_POSTPONED_RESPONSE,
                                RESOURCE_DELETE_OPERATION: CALL_POSTPONED_RESPONSE},
    RESOURCE_UPDATE_OPERATION: {RESOURCE_CREATE_OPERATION: CALL_POSTPONED_RESPONSE,
                                RESOURCE_READ_OPERATION:   CALL_ACCEPTED_RESPONSE,
                                RESOURCE_UPDATE_OPERATION: CALL_POSTPONED_RESPONSE,
                                RESOURCE_DELETE_OPERATION: CALL_POSTPONED_RESPONSE},
    RESOURCE_DELETE_OPERATION: {RESOURCE_CREATE_OPERATION: CALL_POSTPONED_RESPONSE,
                                RESOURCE_READ_OPERATION:   CALL_REJECTED_RESPONSE,
                                RESOURCE_UPDATE_OPERATION: CALL_REJECTED_RESPONSE,
                                RESOURCE_DELETE_OPERATION: CALL_REJECTED_RESPONSE}
}

