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

"""
Contains DTOs to describe events.
"""

# -- constants ----------------------------------------------------------------

# Many more types will be added as this functionality is flushed out

TYPE_REPO_PUBLISH_STARTED = 'repo-publish-started'
TYPE_REPO_PUBLISH_FINISHED = 'repo-publish-finished'

TYPE_REPO_SYNC_STARTED = 'repo-sync-started'
TYPE_REPO_SYNC_FINISHED = 'repo-sync-finished'

# Please keep the following in alphabetical order
# (feel free to change this if there's a simpler way)
ALL_EVENT_TYPES = (TYPE_REPO_PUBLISH_FINISHED, TYPE_REPO_PUBLISH_STARTED,
                   TYPE_REPO_SYNC_FINISHED, TYPE_REPO_SYNC_STARTED,)

# -- classes ------------------------------------------------------------------

class Event(object):

    def __init__(self, event_type, payload):
        self.event_type = event_type
        self.payload = payload

    def __str__(self):
        return 'Event: Type [%s] Payload [%s]' % (self.event_type, self.payload)
