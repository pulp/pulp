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
Handles the CRUD for event listeners.
"""

from pulp.server.db.model.event import EventListener
from pulp.server.exceptions import InvalidValue, MissingResource
from pulp.server.event import notifiers
from pulp.server.event.data import ALL_EVENT_TYPES

# -- manager -----------------------------------------------------------------

class EventListenerManager(object):

    def create(self, notifier_type_id, notifier_config, event_types):
        """
        Creates a new event listener in the server. The listener will listen
        for events of the given types and use the given notifier to react
        to them. The notifier will be passed the given configuration to
        drive how it behaves; values in the configuration vary based on the
        notifier being used.

        For instance, a message bus notifier will likely accept in its
        configuration the message bus and queue on which to broadcast the event.

        @param notifier_type_id: identifies the type of notification to produce
        @type  notifier_type_id: str

        @param notifier_config: used to control how the notifier behaves

        @param event_types: list of event types to listen for; valid values
               can be found in pulp.server.event.notifiers
        @type  event_types: list

        @return: created event listener instance from the database (i.e. _id
                 will be populated)

        @raise InvalidValue: if the notifier or event type ID aren't found
        """

        # Validation
        invalid_event_types = [e for e in event_types if e not in ALL_EVENT_TYPES]
        if len(invalid_event_types) > 0:
            raise InvalidValue(['event_types'])

        if not notifiers.is_valid_notifier_type_id(notifier_type_id):
            raise InvalidValue(['notifier_type_id'])

        # There's no need to check for a conflict; it's possible to use the
        # same notifier for the same event type but a different configuration

        # Create the database entry
        el = EventListener(notifier_type_id, notifier_config, event_types)
        collection = EventListener.get_collection()
        created_id = collection.save(el, safe=True)
        created = collection.find_one(created_id)

        return created

    def delete(self, event_listener_id):
        """
        Deletes the event listener with the given ID. No exception is raised
        if no event listener exists at the given ID.

        @param event_listener_id: database ID for the event listener
        @type  event_listener_id: str
        """
        collection = EventListener.get_collection()
        collection.remove({'_id' : event_listener_id})

    def list(self):
        """
        Returns all event listeners.

        @return: list of event listener SON documents from the database; empty
                 list if there are none
        @rtype:  list
        """
        listeners = list(EventListener.get_collection().find())
        return listeners