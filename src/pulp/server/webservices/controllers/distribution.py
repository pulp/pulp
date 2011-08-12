#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
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

from pulp.server.api.distribution import DistributionApi
from pulp.server.auth.authorization import CREATE, READ, DELETE
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.controllers.decorators import (
    auth_required, error_handler)
from pulp.server.webservices.http import extend_uri_path

# globals ---------------------------------------------------------------------

api = DistributionApi()
log = logging.getLogger('pulp')

# controllers -----------------------------------------------------------------

class Distributions(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self):
        """
        List all available distributions.
        @return: a list of all available distributions
        """
        distributions = api.distributions()
        return self.ok(distributions)


class Distribution(JSONController):

    @error_handler
    @auth_required(READ)
    def GET(self, id):
        """
        Look up distribution by id.
        @param id: distribution id
        @return: distribution info
        """
        # implement filters
        return self.ok(api.distribution(id))

# web.py application ----------------------------------------------------------

URLS = (
    '/$', 'Distributions',
    '/([^/]+)/$', 'Distribution',
)

application = web.application(URLS, globals())
