# -*- coding: utf-8 -*-
#
# Copyright © 2011-2012 Red Hat, Inc.
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

CALL_ENQUEUE_LIFE_CYCLE_CALLBACK = 0
CALL_DEQUEUE_LIFE_CYCLE_CALLBACK = 1
CALL_RUN_LIFE_CYCLE_CALLBACK = 2
CALL_SUCCESS_LIFE_CYCLE_CALLBACK = 3
CALL_FAILURE_LIFE_CYCLE_CALLBACK = 4
CALL_CANCEL_LIFE_CYCLE_CALLBACK = 5
CALL_COMPLETE_LIFE_CYCLE_CALLBACK = 6

CALL_LIFE_CYCLE_CALLBACKS = (CALL_ENQUEUE_LIFE_CYCLE_CALLBACK,
                             CALL_DEQUEUE_LIFE_CYCLE_CALLBACK,
                             CALL_RUN_LIFE_CYCLE_CALLBACK,
                             CALL_SUCCESS_LIFE_CYCLE_CALLBACK,
                             CALL_FAILURE_LIFE_CYCLE_CALLBACK,
                             CALL_CANCEL_LIFE_CYCLE_CALLBACK,
                             CALL_COMPLETE_LIFE_CYCLE_CALLBACK)


_CALL_LIFE_CYCLE_CALLBACK_STRINGS = (
    'enqueue',
    'dequeue',
    'run',
    'success',
    'failure',
    'cancel',
    'complete'
)

def call_life_cycle_callback_to_string(callback_number):
    assert isinstance(callback_number, int)
    assert callback_number >= 0 and callback_number < len(_CALL_LIFE_CYCLE_CALLBACK_STRINGS)
    return _CALL_LIFE_CYCLE_CALLBACK_STRINGS[callback_number]

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
CALL_SKIPPED_STATE = 'skipped'
CALL_RUNNING_STATE = 'running'
CALL_SUSPENDED_STATE = 'suspended'
CALL_FINISHED_STATE = 'finished'
CALL_ERROR_STATE = 'error'
CALL_CANCELED_STATE = 'canceled'
CALL_TIMED_OUT_STATE = 'timed out'

CALL_STATES = (CALL_WAITING_STATE,
               CALL_SKIPPED_STATE,
               CALL_RUNNING_STATE,
               CALL_SUSPENDED_STATE,
               CALL_FINISHED_STATE,
               CALL_ERROR_STATE,
               CALL_CANCELED_STATE,
               CALL_TIMED_OUT_STATE)

CALL_READY_STATES = (CALL_WAITING_STATE,)
CALL_INCOMPLETE_STATES = (CALL_WAITING_STATE, CALL_RUNNING_STATE, CALL_SUSPENDED_STATE)
CALL_COMPLETE_STATES = (CALL_SKIPPED_STATE, CALL_FINISHED_STATE, CALL_ERROR_STATE,
                        CALL_CANCELED_STATE, CALL_TIMED_OUT_STATE)

# resource types ---------------------------------------------------------------

RESOURCE_CDS_TYPE = 'cds'
RESOURCE_CONSUMER_TYPE = 'consumer'
RESOURCE_CONSUMER_BINDING_TYPE = 'consumer_binding'
RESOURCE_CONTENT_UNIT_TYPE = 'content_unit'
RESOURCE_REPOSITORY_TYPE = 'repository'
RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE = 'repository_distributor'
RESOURCE_REPOSITORY_IMPORTER_TYPE = 'repository_importer'
RESOURCE_ROLE_TYPE = 'role'
RESOURCE_SCHEDULE_TYPE = 'schedule'
RESOURCE_USER_TYPE = 'user'

RESOURCE_TYPES = (RESOURCE_CDS_TYPE,
                  RESOURCE_CONSUMER_TYPE,
                  RESOURCE_CONSUMER_BINDING_TYPE,
                  RESOURCE_CONTENT_UNIT_TYPE,
                  RESOURCE_REPOSITORY_TYPE,
                  RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE,
                  RESOURCE_REPOSITORY_IMPORTER_TYPE,
                  RESOURCE_ROLE_TYPE,
                  RESOURCE_SCHEDULE_TYPE,
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


