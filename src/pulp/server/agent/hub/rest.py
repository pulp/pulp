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

import base64
import httplib
import simplejson as json


HOST = 'localhost'
PORT = 443


class NoAuth:

    def header(self):
        return {}

class Basic:

    def __init__(self, user, password):
        self.user = user
        self.password = password

    def header(self):
        plain = ':'.join((self.user, self.password))
        encoded = base64.encodestring(plain)[:-1]
        basic = 'Basic %s' % encoded
        return dict(Authorization=basic)


class Rest:

    def __init__(self, host=HOST, port=PORT, auth=NoAuth()):
        self.http = httplib.HTTPSConnection(host, port)
        self.auth = auth

    def request(self, method, path, body=None):
        try:
            body = json.dumps(body)
        except:
            pass
        self.http.request(
            method,
            path,
            body=body,
            headers=self.auth.header())
        response = self.http.getresponse()
        body = response.read()
        try:
            body = json.loads(body)
        except:
            pass
        return (response.status, body)

    def get(self, path):
        return self.request('GET', path)

    def post(self, path, body=None):
        return self.request('POST', path, body)

    def put(self, path, body=None):
        return self.request('PUT', path, body)

    def delete(self, path, body=None):
        return self.request('DELETE', path, body)

    def __body(self, body):
        if body is None:
            return
        else:
            return json.dumps(body)
