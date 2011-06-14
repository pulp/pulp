# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
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
[[wiki]]
title: Auditing RESTful Interface
description: RESTful interface for querying events audited by the system.
             Events are returned as Event objects.
Event object fields:
 * timestamp, int, time the event occurred
 * principal_type, str, type of the principal
 * principal, str, principal that triggered the event
 * action, str, name of the audited action
 * method, str, name of the method called
 * params, list of str, parameter passed to the method
 * result, str, result of the method call or null if not recorded
 * exception, str, name of the error that occurred, if any
 * traceback, str, code traceback for the error, if any
"""

import web

from pulp.server.auditing import events
from pulp.server.auth.authorization import READ
from pulp.server.webservices import mongo
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import (
    auth_required, error_handler)

# audit events controller -----------------------------------------------------

class Events(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self):
        """
        [[wiki]]
        title: List Audited Events
        description: List all available audited events.
        method: GET
        path: /events/
        permission: READ
        success response: 200 OK
        failure response: None
        return: list of event objects
        filters:
         * api, str, the api name
         * method, str, the method name
         * principal, str, the caller of an api method
         * field, str, which fields are returned for each event
         * limit, int, limit the number of events returned
         * errors_only, bool, only show events that have a traceback associated with them
        """
        valid_filters = ('principal', 'api', 'method', 'field', 'limit', 'errors_only')
        filters = self.filters(valid_filters)

        errors_only_flag = filters.pop('errors_only', ['false'])[0].lower()
        errors_only = errors_only_flag in ('true', 'yes', '1')

        limit = filters.pop('limit', None)
        if limit is not None:
            try:
                limit = int(limit[-1]) # last limit takes precedence
            except ValueError:
                return self.bad_request('Invalid value for limit parameter')

        fields = filters.pop('field', None)
        spec = mongo.filters_to_re_spec(filters)
        return self.ok(events(spec, fields, limit, errors_only))

# web.py application ----------------------------------------------------------

URLS = (
    '/$', Events,
)

application = web.application(URLS, globals())
