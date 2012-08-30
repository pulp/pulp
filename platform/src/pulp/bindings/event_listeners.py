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

from pulp.bindings.base import PulpAPI

class EventListenerAPI(PulpAPI):
    PATH = 'v2/events/'

    def list(self):
        """
        List all of the event listeners

        :return: list of event listener documents
        :rtype:  list
        """
        return self.server.GET(self.PATH).response_body

    def create(self, notifier_type_id, notifier_config, event_types):
        """
        Create a new event listener

        :param notifier_type_id: the type of notification handler
        :type  notifier_type_id: srt
        :param notifier_config: dict with config values required by the
                                notifier type
        :type notifier_config:  dict
        :param event_types: list of event types to listen for
        :type event_types:  list
        """

        body = {
            'notifier_type_id' : notifier_type_id,
            'notifier_config' : notifier_config,
            'event_types' : event_types
        }
        return self.server.POST(self.PATH, body).response_body

    def update(self, listener_id, notifier_config=None, event_types=None):
        """
        Update an event listener

        :param listener_id: id of an event listener
        :type  listener_id: str
        :param notifier_config: dict with config values required by the
                                notifier type
        :type notifier_config:  dict
        :param event_types: list of event types to listen for
        :type event_types:  list
        """

        body = {}
        if notifier_config is not None:
            body['notifier_config'] = notifier_config
        if event_types is not None:
            body['event_types'] = event_types
        path = self.PATH + str(listener_id) + '/'
        return self.server.PUT(path, body)

    def delete(self, listener_id):
        """
        Delete an event listener

        :param listener_id: id of an event listener
        :type  listener_id: str
        """

        path = self.PATH + str(listener_id) + '/'
        return self.server.DELETE(path)

