#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import oauth2 as oauth
import os
import sys
import web

from paste.fixture import TestApp

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.server.auth import authorization
from pulp.server.webservices import application
from pulp.server.webservices import http

class TestOauth(testutil.PulpAsyncTest):

    def setUp(self):
        testutil.PulpAsyncTest.setUp(self)
        self.web_app = web.subdir_application(application.URLS)
        self.test_app = TestApp(self.web_app.wsgifunc())

        def request_info(key):
            if key == "REQUEST_URI":
                key = "PATH_INFO"

            return web.ctx.environ.get(key, None)

        self.mock(http, "request_info", request_info)

        self.user_api.create("admin")
        self.user_api.update("admin",
            dict(roles=authorization.super_user_role))

    def tearDown(self):
        self.user_api.delete("admin")
        testutil.PulpAsyncTest.tearDown(self)

    def test_oauth_header(self):
        CONSUMER_KEY = 'some-key'
        CONSUMER_SECRET = 'some-secret'
        URL = "http://localhost/repositories/"

        consumer = oauth.Consumer(CONSUMER_KEY, CONSUMER_SECRET)

        # Formulate a OAuth request with the embedded consumer with key/secret pair
        oauth_request = oauth.Request.from_consumer_and_token(consumer, http_method="GET", http_url=URL)
        # Sign the Request.  This applies the HMAC-SHA1 hash algorithm
        oauth_request.sign_request(oauth.SignatureMethod_HMAC_SHA1(), consumer, None)

        headers = dict(oauth_request.to_header().items() + {'pulp-user':'admin'}.items())

        response = self.test_app.get('http://localhost/repositories/', headers=headers)

        self.assertEquals(200, response.status)
