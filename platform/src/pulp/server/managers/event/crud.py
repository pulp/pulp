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
from bson.errors import InvalidId
import sys

from pulp.server.compat import ObjectId
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
        _validate_event_types(event_types)

        if not notifiers.is_valid_notifier_type_id(notifier_type_id):
            raise InvalidValue(['notifier_type_id'])

        # There's no need to check for a conflict; it's possible to use the
        # same notifier for the same event type but a different configuration

        # Make sure the configuration is at very least empty
        if notifier_config is None:
            notifier_config = {}

        # Create the database entry
        el = EventListener(notifier_type_id, notifier_config, event_types)
        collection = EventListener.get_collection()
        created_id = collection.save(el, safe=True)
        created = collection.find_one(created_id)

        return created

    def get(self, event_listener_id):
        """
        Retrieves the given event listener if it exists. If not, an exception
        is raised.

        @param event_listener_id: listener to retrieve
        @type  event_listener_id: str

        @return: listener instance from the database
        @rtype:  dict

        @raise MissingResource: if no listener exists at the given ID
        """
        collection = EventListener.get_collection()

        try:
            id = ObjectId(event_listener_id)
        except InvalidId:
            raise MissingResource(event_listener=event_listener_id), None, sys.exc_info()[2]

        listener = collection.find_one({'_id' : id})

        if listener is None:
            raise MissingResource(event_listener=event_listener_id)
        else:
            return listener

    def delete(self, event_listener_id):
        """
        Deletes the event listener with the given ID. No exception is raised
        if no event listener exists at the given ID.

        @param event_listener_id: database ID for the event listener
        @type  event_listener_id: str

        @raise MissingResource: if no listener exists at the given ID
        """
        collection = EventListener.get_collection()

        self.get(event_listener_id) # check for MissingResource

        collection.remove({'_id' : ObjectId(event_listener_id)})

    def update(self, event_listener_id, notifier_config=None, event_types=None):
        """
        Changes the configuration of an existing event listener. The notifier
        type cannot be changed; in such cases the event listener should be
        deleted and a new one created.

        If specified, the notifier_config follows the given conventions:
        - If a key is specified with a value of None, the effect is that the
          key is removed from the configuration
        - If an existing key is unspecified, its value is unaffected

        Event types must be the *complete* list of event types to listen for.
        This method does not support deltas on the event types.

        @param event_listener_id: listener being edited
        @type  event_listener_id: str

        @param notifier_config: contains only configuration properties to change
        @type  notifier_config: dict

        @param event_types: complete list of event types that should be fired on
        @type  event_types: list

        @return: updated listener instance from the database
        """
        collection = EventListener.get_collection()

        # Validation
        existing = self.get(event_listener_id) # will raise MissingResource

        # Munge the existing configuration if it was specified
        if notifier_config is not None:
            munged_config = dict(existing['notifier_config'])

            remove_us = [k for k in notifier_config.keys() if notifier_config[k] is None]
            for k in remove_us:
                munged_config.pop(k, None)
                notifier_config.pop(k)

            munged_config.update(notifier_config)
            existing['notifier_config'] = munged_config

        # Update the event list
        if event_types is not None:
            _validate_event_types(event_types)
            existing['event_types'] = event_types

        # Update the database
        collection.save(existing, safe=True)

        # Reload to return
        existing = collection.find_one({'_id' : ObjectId(event_listener_id)})
        return existing

    def list(self):
        """
        Returns all event listeners.

        @return: list of event listener SON documents from the database; empty
                 list if there are none
        @rtype:  list
        """
        listeners = list(EventListener.get_collection().find())
        return listeners

def _validate_event_types(event_types):
    if not isinstance(event_types, (tuple, list)) or len(event_types) is 0:
        raise InvalidValue(['event_types'])

    invalid_event_types = [e for e in event_types if e not in ALL_EVENT_TYPES]
    if len(invalid_event_types) > 0:
        raise InvalidValue(['event_types'])
