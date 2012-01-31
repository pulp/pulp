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


class StartResponse(object):

    def __init__(self):
        self.status = None
        self.headers = {}

    def __call__(self, status, headers):
        self.status = status
        self.headers.update(dict(headers))

    def clear_headers(self):
        self.headers = {}

    def add_header(self, field, value):
        self.headers[field] = value

    def remove_header(self, field):
        self.headers.pop(field, None)


class StartResponseMiddleware(object):

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        obj = StartResponse()
        values = self.app(environ, obj)
        start_response(obj.status, list(obj.headers.items()))
        return values
