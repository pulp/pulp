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
Contains controllers for API root-level actions. Putting functionality under
this area should be very rare and only in the cases where it absolutely does
not fit into a resource collection.
"""

import logging

# 3rd Party
import web

# Pulp
from pulp.server.auth.authorization import READ
from pulp.server.managers import factory
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import auth_required

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- controllers --------------------------------------------------------------

class LoginController(JSONController):

    @auth_required(READ)
    def POST(self):
        user_manager = factory.user_manager()

        certificate = user_manager.generate_user_certificate()
        return self.ok(certificate)

# -- web.py application -------------------------------------------------------

# These are defined under /v2/actions/ (see application.py to double-check)
urls = (
    '/login/', 'LoginController',
)

application = web.application(urls, globals())