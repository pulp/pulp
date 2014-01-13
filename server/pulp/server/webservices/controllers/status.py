# -*- coding: utf-8 -*-
#
# Copyright © 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

"""
Unauthenticated status API so that other can make sure we're up (to no good).
"""

import web

from pulp import __version__

from pulp.server.webservices.controllers.base import JSONController

# status controller ------------------------------------------------------------

class StatusController(JSONController):

    #: Always the full version. Ex: 2.3.1
    _server_version = __version__
    #: Always the current supported api version in x.y format. Ex: 2.3
    _api_version = ".".join(__version__.split('.')[0:2])

    def GET(self):
        status_data = {
            'api_version': self._api_version,
            'server_version': self._server_version,
        }
        return self.ok(status_data)

# web.py application -----------------------------------------------------------

URLS = ('/', StatusController)

application = web.application(URLS, globals())
