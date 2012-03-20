# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

# Python
import logging

# 3rd Party
import web

# Pulp
from pulp.server.auth.authorization import UPDATE
from pulp.server.dispatch import factory as dispatch_factory
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required, error_handler

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- controllers --------------------------------------------------------------


class Reply(JSONController):

    @error_handler
    @auth_required(UPDATE)
    def POST(self, uuid):
        """
        Agent (asynchronous) RMI call back.
        Update the related task by ID.
        """
        body = self.params()
        _LOG.info('agent (%s) reply:\n%s', uuid, body)
        coordinator = dispatch_factory.coordinator()
        task_id = body['any']
        if body['status'] == 200:
            result = body['reply']
            coordinator.complete_call_success(task_id, result)
        else:
            raised = body['exception']
            exception = raised['xmsg']
            traceback = raised['xstate']['trace']
            coordinator.complete_call_failure(task_id, exception, traceback)
        return self.ok({})

# -- web.py application -------------------------------------------------------

urls = (
    '/([^/]+)/reply/$', 'Reply',
)

application = web.application(urls, globals())
