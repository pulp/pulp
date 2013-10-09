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
