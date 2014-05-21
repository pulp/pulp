# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# key used in a repository's "notes" field with a value describing what type
# of content is in the repository.
REPO_NOTE_TYPE_KEY = '_repo-type'

# Maps user entered query sort parameters to the pymongo representation
SORT_ASCENDING = 'ascending'
SORT_DESCENDING = 'descending'
# We are using constant values of pymongo.ASCENDING and pymongo.DESCENDING
# to avoid every consumer having a dependency on pymongo just for these constants.
SORT_DIRECTION = {
    SORT_ASCENDING: 1,
    SORT_DESCENDING: -1,
}

# Strings for repository history filters
REPO_HISTORY_FILTER_LIMIT = 'limit'
REPO_HISTORY_FILTER_SORT = 'sort'
REPO_HISTORY_FILTER_START_DATE = 'start_date'
REPO_HISTORY_FILTER_END_DATE = 'end_date'

# Maximum number of units that should be displayed at one time by the command line
DISPLAY_UNITS_DEFAULT_MAXIMUM = 100

# call states ------------------------------------------------------------------

CALL_WAITING_STATE = 'waiting'
CALL_SKIPPED_STATE = 'skipped'
CALL_ACCEPTED_STATE = 'accepted'
CALL_RUNNING_STATE = 'running'
CALL_SUSPENDED_STATE = 'suspended'
CALL_FINISHED_STATE = 'finished'
CALL_ERROR_STATE = 'error'
CALL_CANCELED_STATE = 'canceled'
CALL_TIMED_OUT_STATE = 'timed out'

CALL_INCOMPLETE_STATES = (CALL_WAITING_STATE, CALL_ACCEPTED_STATE, CALL_RUNNING_STATE,
                          CALL_SUSPENDED_STATE)
CALL_COMPLETE_STATES = (CALL_SKIPPED_STATE, CALL_FINISHED_STATE, CALL_ERROR_STATE,
                        CALL_CANCELED_STATE, CALL_TIMED_OUT_STATE)
