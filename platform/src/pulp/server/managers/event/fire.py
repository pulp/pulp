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
Handles the firing of events to any configured listeners. This module is
responsible for defining what events look like. The specific fire methods for
each event type require data relevant to that event type and package it up
in a consistent event format for that type.
"""

import logging

from pulp.server.db.model.event import EventListener
from pulp.server.event import notifiers
from pulp.server.event import data as e

_LOG = logging.getLogger(__name__)

class EventFireManager(object):

    # -- specific event fire methods ------------------------------------------

    def fire_repo_sync_started(self, repo_id):
        """
        Fires an event indicating the given repository has started a sync.
        """
        payload = {'repo_id' : repo_id}
        self._do_fire(e.Event(e.TYPE_REPO_SYNC_STARTED, payload))

    def fire_repo_sync_finished(self, sync_result):
        """
        Fires an event indicating the given repository has completed a sync.
        The success/failure of the sync, timestamp information, and sync report
        provided by the importer are all included in the sync_result.

        @param sync_result: DB object describing the sync result
        @type  sync_result: dict
        """
        sync_result.pop('_id', None)
        self._do_fire(e.Event(e.TYPE_REPO_SYNC_FINISHED, sync_result))

    def fire_repo_publish_started(self, repo_id, distributor_id):
        """
        Fires an event indicating the given repository's distributor has started
        a publish.
        """
        payload = {'repo_id' : repo_id, 'distributor_id' : distributor_id}
        self._do_fire(e.Event(e.TYPE_REPO_PUBLISH_STARTED, payload))

    def fire_repo_publish_finished(self, publish_result):
        """
        Fires an event indicating the given repository has completed a publish.
        The success/failure of the publish, timestamp information, and publish report
        provided by the distributor are all included in the publish_result.
        """
        publish_result.pop('_id', None)
        self._do_fire(e.Event(e.TYPE_REPO_PUBLISH_FINISHED, publish_result))

    # -- private --------------------------------------------------------------

    def _do_fire(self, event):
        """
        Performs the actual act of firing an event to all appropriate
        listeners. This call will log but otherwise suppress any exception
        that comes out of a notifier.

        @param event: event object to fire
        @type  event: pulp.server.event.data.Event
        """

        # Determine which listeners should be notified
        listeners = list(EventListener.get_collection().find({'event_types' : event.event_type}))

        # For each listener, retrieve the notifier and invoke it. Be sure that
        # an exception from a notifier is logged but does not interrupt the
        # remainder of the firing, nor bubble up.
        for l in listeners:
            notifier_type_id = l['notifier_type_id']
            f = notifiers.get_notifier_function(notifier_type_id)

            try:
                f(l['notifier_config'], event)
            except Exception:
                _LOG.exception('Exception from notifier of type [%s]' % notifier_type_id)