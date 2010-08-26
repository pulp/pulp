#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

# Python
import logging

# 3rd Party
import web

# Pulp
from pulp.server.api.auth import AuthApi
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.webservices.role_check import RoleCheck


# globals ---------------------------------------------------------------------

auth_api = AuthApi()
log = logging.getLogger(__name__)

# controllers -----------------------------------------------------------------

class AdminAuthCertificates(JSONController):

    @JSONController.error_handler
    @RoleCheck(admin=True)
    def GET(self):
        '''
        Creates and returns an authentication certificate for the currently
        logged in user.
        '''
        private_key, cert = auth_api.admin_certificate()
        certificate = {'certificate': cert, 'private_key': private_key}
        return self.ok(certificate)

# web.py application ----------------------------------------------------------

URLS = (
    '/admin_certificate/$', 'AdminAuthCertificates',
)

application = web.application(URLS, globals())