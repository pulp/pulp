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

# resource types ---------------------------------------------------------------

RESOURCE_CONSUMER_TYPE = 'consumer'
RESOURCE_CONTENT_UNIT_TYPE = 'content_unit'
RESOURCE_REPOSITORY_TYPE = 'repository'
RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE = 'repository_distributor'
RESOURCE_REPOSITORY_IMPORTER_TYPE = 'repository_importer'
RESOURCE_REPOSITORY_GROUP_TYPE = 'repository_group'
RESOURCE_REPOSITORY_GROUP_DISTRIBUTOR_TYPE = 'repository_group_distributor'
RESOURCE_REPOSITORY_PROFILE_APPLICABILITY_TYPE = 'repository_profile_applicability'

# any resource id --------------------------------------------------------------

RESOURCE_ANY_ID = "RESOURCE_ANY_ID"

