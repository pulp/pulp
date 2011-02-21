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

from pulp.server.api.file import FileApi
from pulp.server.api.repo import RepoApi
from pulp.server.auth.authorization import READ, EXECUTE
from pulp.server.webservices.controllers.base import JSONController

# globals ---------------------------------------------------------------------

api = FileApi()
rapi = RepoApi()
log = logging.getLogger('pulp')

class File(JSONController):
    
    @JSONController.error_handler
    @JSONController.auth_required(READ)
    def GET(self, id):
        """
        Get a file
        @param id: file id
        @return: file object
        """
        return self.ok(api.file(id))

# web.py application ----------------------------------------------------------

URLS = (
    '/files/([^/]+)/$', 'File',
)

application = web.application(URLS, globals())
