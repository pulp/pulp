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


import web
import logging
import base64
from pulp.server.webservices import http
from pulp.server.webservices.controllers.base import JSONController
from pulp.server.api.upload import File


log = logging.getLogger(__name__)


class Start(JSONController):

    @JSONController.error_handler
    def POST(self):
        request = self.params()
        name = request['name']
        checksum = request['checksum']
        size = request['size']
        f = File.open(name, checksum, size)
        offset = f.next()
        d = dict(id=f.id, offset=offset)
        return self.ok(d)


class Append(JSONController):

    @JSONController.error_handler
    def POST(self, id):
        f = File(id)
        segment = self.params()
        encoding = segment['encoding']
        content = segment['content']
        f.append(base64.b64decode(content))
        return self.ok(True)

URLS = (
    '/$', 'Start',
    '/([^/]+)/$', 'Append',
    )

application = web.application(URLS, globals())
