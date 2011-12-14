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
CALL_FINISH_EXECUTION_HOOK = 3
CALL_ERROR_EXECUTION_HOOK = 4
CALL_CANCEL_EXECUTION_HOOK = 5

CALL_EXECUTION_HOOKS = (CALL_ENQUEUE_EXECUTION_HOOK,
                        CALL_DEQUEUE_EXECUTION_HOOK,
                        CALL_RUN_EXECUTION_HOOK,
                        CALL_FINISH_EXECUTION_HOOK,
                        CALL_ERROR_EXECUTION_HOOK,
                        CALL_CANCEL_EXECUTION_HOOK)

# control hooks ----------------------------------------------------------------

CALL_CANCEL_CONTROL_HOOK = 0
CALL_PROGRESS_CONTROL_HOOK = 1
CALL_PRESENTATION_CONTROL_HOOK = 2

CALL_CONTROL_HOOKS = (CALL_CANCEL_CONTROL_HOOK,
                      CALL_PRESENTATION_CONTROL_HOOK,
                      CALL_PRESENTATION_CONTROL_HOOK)

# execution responses ----------------------------------------------------------

CALL_ACCEPTED_RESPONSE = 'call request accepted'
CALL_POSTPONED_RESPONSE = 'call request postponed'
CALL_REJECTED_RESPONSE = 'call request rejected'

CALL_RESPONSES = (CALL_ACCEPTED_RESPONSE,
                  CALL_POSTPONED_RESPONSE,
                  CALL_REJECTED_RESPONSE)

# call states ------------------------------------------------------------------

CALL_WAITING_STATE = 'call waiting'
CALL_RUNNING_STATE = 'call running'
CALL_SUSPENDED_STATE = 'call suspended'
CALL_FINISHED_STATE = 'call finished'
CALL_ERROR_STATE = 'call error'
CALL_CANCELED_STATE = 'call canceled'

CALL_STATES = (CALL_WAITING_STATE,
               CALL_RUNNING_STATE,
               CALL_SUSPENDED_STATE,
               CALL_FINISHED_STATE,
               CALL_ERROR_STATE,
               CALL_CANCELED_STATE)

CALL_READY_STATES = (CALL_WAITING_STATE,)
CALL_INCOMPLETE_STATES = (CALL_WAITING_STATE, CALL_RUNNING_STATE, CALL_SUSPENDED_STATE)
CALL_COMPLETE_STATES = (CALL_FINISHED_STATE, CALL_ERROR_STATE, CALL_CANCELED_STATE)
