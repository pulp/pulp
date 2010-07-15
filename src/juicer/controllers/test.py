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

import logging
import web

from juicer.controllers.base import JSONController
from juicer.role_check import RoleCheck

log = logging.getLogger('pulp')

class Index(JSONController):
    
    def GET(self):
        valid_filters = ('name', 'occupation')
        filters = self.filters(valid_filters)
        return self.ok(filters)
    
    def HEAD(self):
        # should get through, but shouldn't return the body
        return self.ok(False)
    
    def POST(self):
        params = self.params()
        return self.ok(params)
    
    def PUT(self):
        params = self.params()
        return self.created(params)
    
    def DELETE(self):
        return self.ok(True)
    
    def TRACE(self):
        # should get through, but shouldn't return the body
        return self.ok(True)
    
    def OPTIONS(self):
        return self.ok(True)
    
    def CONNECT(self):
        # proxy-only command, most likely not supported
        return self.ok(False)
    
    
class AuthTest(JSONController):
    #https://localhost:8811/test/some-id/auth/
    @RoleCheck(admin=True, consumer=True)
    def GET(self, id):
        log.error("AuthTest.GET")
        ret = {'idparam': id}
        return self.ok(ret)
    
# web.py application ----------------------------------------------------------

URLS = (
    '/$', 'Index',
    '/([^/]+)/auth/$', 'AuthTest'
)

application = web.application(URLS, globals())