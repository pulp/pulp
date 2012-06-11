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

import web

from pulp.server.webservices import serialization
from pulp.server.webservices.controllers.base import JSONController


class V2API(JSONController):

    def GET(self):
        links = {
            'content': serialization.link.child_link_obj('content'),
            'plugins': serialization.link.child_link_obj('plugins'),
            'repositories': serialization.link.child_link_obj('repositories'),
        }
        return self.ok(links)

    def OPTIONS(self):
        link = serialization.link.current_link_obj()
        link.update({'methods': ['GET']})
        return self.ok(link)

# web.py application

_URLS = ('/$', V2API)
application = web.application(_URLS, globals())
