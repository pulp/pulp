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
Simple wsgi server that user web.py in order to experiment request possibilities.
"""

from pprint import pformat

import web

import srv


class ParamsServer(srv.Server):

    def GET(self, path):
        params = web.input()
        self.ok()
        return pformat(params)

urls = ('/(.*)', 'ParamsServer')
application = web.application(urls, globals())
srv.start_server(application.wsgifunc())


def request(d={}):
    assert d
    params = []
    for k, v in d.items():
        if isinstance(v, (list, tuple)):
            params.extend('%s=%s' % (k, _) for _ in v)
            continue
        params.append('%s=%s' % (k, v))
    status, body = srv.GET('/?' + '&'.join(params))
    print body


def raw(s):
    assert s
    status, body = srv.GET('/?' + s)
    print body
