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
"""
Simple wsgi server that can be used to run generic apps
"""

import httplib
import threading
from wsgiref import simple_server

import web



_server_port = None


class Server(object):

    def _status(self, code):
        web.ctx.status = '%d %s'  % (code, httplib.responses[code])

    def ok(self):
        self._status(httplib.OK)

    def created(self):
        self._status(httplib.CREATED)

    def no_content(self):
        self._status(httplib.NO_CONTENT)

    def accepted(self):
        self._status(httplib.ACCEPTED)

    def bad_request(self):
        self._status(httplib.BAD_REQUEST)

    def unauthorized(self):
        self._status(httplib.UNAUTHORIZED)

    def not_found(self):
        self._status(httplib.NOT_FOUND)

    def method_not_allowed(self):
        self._status(httplib.METHOD_NOT_ALLOWED)

    def not_acceptable(self):
        self._status(httplib.NOT_ACCEPTABLE)

    def conflict(self):
        self._status(httplib.CONFLICT)

    def internal_server_error(self):
        self._status(httplib.INTERNAL_SERVER_ERROR)



def start_server(app, port=8888):
    global _server_port
    assert _server_port is None
    web.config.debug = False
    server = simple_server.make_server('', port, app)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.setDaemon(True)
    server_thread.start()
    _server_port = port
    print 'server listening on port %d' % port


def server_tuple():
    assert _server_port is not None
    return ('localhost', _server_port)


def request(method, path, body=None, headers={}):
    assert _server_port is not None
    connection = httplib.HTTPConnection(*server_tuple())
    connection.request(method, path, body, headers)
    response = connection.getresponse()
    return (response.status, response.read())


def GET(path, headers={}):
    return request('GET', path, headers=headers)


def POST(path, body=None, headers={}):
    return request('POST', path, body, headers)


def DELETE(path, headers={}):
    return request('DELETE', path, headers=headers)


def PUT(path, body, headers={}):
    return request('PUT', path, body, headers)
