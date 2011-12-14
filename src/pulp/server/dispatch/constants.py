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

# TODO task events

# execution responses ----------------------------------------------------------

CALL_ACCEPTED = 'call request accepted'
CALL_POSTPONED = 'call request postponed'
CALL_REJECTED = 'call request rejected'

CALL_RESPONSES = (CALL_ACCEPTED,
                  CALL_POSTPONED,
                  CALL_REJECTED)

# call states ------------------------------------------------------------------

CALL_WAITING = 'call waiting'
CALL_RUNNING = 'call running'
CALL_SUSPENDED = 'call suspended'
CALL_FINISHED = 'call finished'
CALL_ERROR = 'call error'
CALL_CANCELED = 'call canceled'

CALL_STATES = (CALL_WAITING,
               CALL_RUNNING,
               CALL_SUSPENDED,
               CALL_FINISHED,
               CALL_ERROR,
               CALL_CANCELED)

CALL_READY_STATES = (CALL_WAITING,)
CALL_INCOMPLETE_STATES = (CALL_WAITING, CALL_RUNNING, CALL_SUSPENDED)
CALL_COMPLETE_STATES = (CALL_FINISHED, CALL_ERROR, CALL_CANCELED)
