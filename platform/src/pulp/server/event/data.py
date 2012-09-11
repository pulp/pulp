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

from pulp.server.dispatch import factory as dispatch_factory

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
        self.call_report = self._get_call_report()

    def __str__(self):
        return 'Event: Type [%s] Payload [%s]' % (self.event_type, self.payload)

    def _get_call_report(self):
        context = dispatch_factory.context()
        coordinator = dispatch_factory.coordinator()
        call_report_list = coordinator.find_call_reports(task_id=context.task_id)
        if not call_report_list:
            return None
        return call_report_list[0].serialize()

