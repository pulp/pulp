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

import logging
import web

from pulp.common.util import decode_unicode
from pulp.server.auth.authorization import CREATE, READ, DELETE, UPDATE
from pulp.server.managers import factory as manager_factory
from pulp.server.webservices.serialization import link
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- controllers --------------------------------------------------------------

class EventCollection(JSONController):

    # Scope: Collection
    # GET:   Retrieve event listeners (types and configuration)
    # POST:  Create a new event listener

    @auth_required(READ)
    def GET(self):
        manager = manager_factory.event_listener_manager()
        managers = manager.list()

        for m in managers:
            href = link.current_link_obj()
            m.update(href)

        return self.ok(managers)

    @auth_required(CREATE)
    def POST(self):
        # Parameters
        params = self.params()

        notifier_type_id = params.get('notifier_type_id', None)
        notifier_config = params.get('notifier_config', None)
        event_types = params.get('event_types', None)

        # Execution
        manager = manager_factory.event_listener_manager()
        created = manager.create(notifier_type_id, notifier_config, event_types)

        href = link.child_link_obj(created['id'])
        created.update(href)

        return self.created(href['_href'], created)

class EventResource(JSONController):

    # Scope:  Resource
    # GET:    Retrieve a single event listener
    # DELETE: Delete an event listener
    # PUT:    Update the configuration or event types for an existing listener

    @auth_required(READ)
    def GET(self, event_listener_id):
        manager = manager_factory.event_listener_manager()

        event_listener_id = decode_unicode(event_listener_id)

        listener = manager.get(event_listener_id) # will raise MissingResource
        href = link.current_link_obj()
        listener.update(href)

        return self.ok(listener)

    @auth_required(DELETE)
    def DELETE(self, event_listener_id):
        manager = manager_factory.event_listener_manager()

        manager.delete(event_listener_id) # will raise MissingResource

        return self.ok(None)

    @auth_required(UPDATE)
    def PUT(self, event_listener_id):
        # Parameters
        params = self.params()

        notifier_config = params.get('notifier_config', None)
        event_types = params.get('event_types', None)

        # Execution
        manager = manager_factory.event_listener_manager()
        updated = manager.update(event_listener_id, notifier_config=notifier_config, event_types=event_types)

        href = link.current_link_obj()
        updated.update(href)

        return self.ok(updated)

# -- web.py application -------------------------------------------------------

# These are defined under /v2/event_listeners/ (see application.py to double-check)
URLS = (
    '/', 'EventCollection', # collection
    '/([^/]+)/$', 'EventResource', # resource
)

application = web.application(URLS, globals())