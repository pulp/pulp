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

from pulp.server.db.model.base import Model

class EventListener(Model):
    """
    Represents a configured event listener. Each instance will define a
    notifier by its type and configuration and indicate which event types
    to listen for.

    @ivar notifier_type_id: identifies the notifier that will be used to
          handle the event
    @type notifier_type_id: str

    @ivar notifier_config: configuration for the notifier, passed in each time
          an event this listener cares about is fired
    @type notifier_config: dict

    @ivar event_types: list of event types that this listener will handle
    @type event_types: list
    """

    collection_name = 'event_listeners'

    def __init__(self, notifier_type_id, notifier_config, event_types):
        super(EventListener, self).__init__()

        self.notifier_type_id = notifier_type_id
        self.notifier_config = notifier_config
        self.event_types = event_types