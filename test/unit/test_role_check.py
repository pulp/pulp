#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
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
import base64
import logging
import os
import sys
import oauth2 as oauth
import unittest
import time
import web

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

from pulp.server import config as pulp_config
from pulp.server.api.user import UserApi
from pulp.server.api.consumer import ConsumerApi
from pulp.server.auth import principal
import pulp.server.auth.cert_generator as cert_generator
from pulp.server.auth.cert_generator import SerialNumber
from pulp.server.auth.certificate import Certificate
from pulp.server.webservices.role_check import RoleCheck
import testutil

SerialNumber.PATH = '/tmp/sn.dat'


class TestRoleCheck(unittest.TestCase):

    def setUp(self):
        self.config = testutil.load_test_config()
        self.uapi = UserApi()
        self.capi = ConsumerApi()
        sn = SerialNumber()
        sn.reset()

        # Make sure to reset the principal between tests
        principal.set_principal(principal.SystemPrincipal())

    def tearDown(self):
        self.uapi.clean()
        self.capi.clean()
        testutil.common_cleanup()

    @RoleCheck(consumer=True)
    def consumer_only(self, someparam, otherparam):
        print "some method executed"
        return otherparam

    @RoleCheck(admin=True)
    def admin_only(self, someparam, otherparam):
        print "some_other_method executed"
        return otherparam

    @RoleCheck(admin=True, consumer=True)
    def consumer_and_admin(self, someparam, otherparam):
        print "some_other_method2 executed"
        return otherparam

    @RoleCheck(admin=True, consumer_id=True)
    def consumer_id_and_admin(self, consumer_id, otherparam):
        print "some_other_method3 executed"
        return otherparam

    def test_consumer_cert(self):
        # Setup
        consumer_uid = "some-id-cert-test"
        self.capi.create(consumer_uid, "desc")

        temp_pk, temp_cert = cert_generator.make_cert(consumer_uid)
        self.assertTrue(temp_cert is not None)

        web.ctx['headers'] = []
        web.ctx['environ'] = dict()
        web.ctx.environ['SSL_CLIENT_CERT'] = temp_cert

        # Tests
        retval = self.consumer_only("blippy", "baz")
        self.assertEquals(retval, "baz")

        #   Test that both the cert + id *in* the cert match
        retval = self.consumer_id_and_admin(consumer_uid, "baz")
        self.assertEquals(retval, "baz")

        #   Test the opposite, good cert, bad param
        retval = self.consumer_id_and_admin("fake-consumer-uid", "baz")
        self.assertNotEquals(retval, "baz")

        #   Test with non-existing consumer (not in the DB)
        consumer_uid = "non-existing-consumer"
        (temp_pk, temp_cert) = cert_generator.make_cert(consumer_uid)

        web.ctx.environ['SSL_CLIENT_CERT'] = temp_cert

        retval = self.consumer_only(consumer_uid, "baz")
        self.assertNotEquals(retval, "baz")

    def test_consumer_cert_foreign_ca(self):
        # Setup
        data_dir = os.path.abspath(os.path.dirname(__file__))
        test_cert = data_dir + '/data/test_cert_bad_ca.pem'
        cert = Certificate()
        cert.read(test_cert)

        # Test
        web.ctx['headers'] = []
        web.ctx['environ'] = dict()
        web.ctx.environ['SSL_CLIENT_CERT'] = cert.toPEM()

        # Test
        self.consumer_only('somevalue')
        self.assertTrue(web.ctx.status.startswith('401'))

    def test_admin_cert(self):
        # Setup
        admin = self.uapi.create('test-admin', 'test-admin')
        pk, cert_pem = cert_generator.make_admin_user_cert(admin)

        web.ctx['headers'] = []
        web.ctx['environ'] = dict()
        web.ctx.environ['SSL_CLIENT_CERT'] = cert_pem

        # Test
        retval = self.admin_only('foo', 'baz')
        self.assertEqual(retval, 'baz')

    def test_username_pass(self):
        # Setup

        web.ctx['headers'] = []
        web.ctx['environ'] = dict()

        #   Create a user
        login = "test_auth"
        password = "some password"
        self.uapi.create(login, password=password)

        # Test
        #   Check we can't run the method with no setup in web
        retval = self.admin_only('somevalue', 'baz')
        self.assertNotEqual(retval, 'baz')

        #   Check with bad password
        loginpass = "%s:%s" % (login, "invalid password")
        encoded = base64.encodestring(loginpass)
        web.ctx.environ['HTTP_AUTHORIZATION'] = "Basic %s" % encoded

        retval = self.admin_only('somevalue', 'baz')
        self.assertNotEqual(retval, 'baz')

        #   Check with bad username
        loginpass = "%s:%s" % ("non existing user", password)
        encoded = base64.encodestring(loginpass)
        web.ctx.environ['HTTP_AUTHORIZATION'] = "Basic %s" % encoded

        retval = self.admin_only('somevalue', 'baz')
        self.assertNotEqual(retval, 'baz')

        #   Check a successful test
        loginpass = "%s:%s" % (login, password)
        encoded = base64.encodestring(loginpass)
        web.ctx.environ['HTTP_AUTHORIZATION'] = "Basic %s" % encoded

        retval = self.admin_only('somevalue', 'baz')
        self.assertEquals(retval, 'baz')

    def test_oauth(self):
        web.ctx['headers'] = []
        web.ctx['environ'] = dict()

        #   Create a user
        login = "test_auth"
        password = "some password"
        self.uapi.create(login, password=password)

        key = self.config.get('security', 'oauth_key')
        secret = self.config.get('security', 'oauth_secret')
        scheme = "https"
        host = "localhost.example.com"
        path = "/blah/blippy"
        url = "%s://%s%s" % (scheme, host, path)

        oauth_string = self._create_oauth_signature(key, secret, url)

        web.ctx.environ['wsgi.url_scheme'] = scheme
        web.ctx.environ['HTTP_HOST'] = host
        web.ctx.environ['REQUEST_URI'] = path
        web.ctx.environ['REQUEST_METHOD'] = "GET"
        web.ctx.environ['HTTP_AUTHORIZATION'] = "OAuth %s" % oauth_string
        web.ctx.environ['HTTP_PULP_USER'] = login

        # Check for good oauth signature
        retval = self.admin_only('somevalue', 'baz')
        self.assertEquals(retval, 'baz')

        # Check for bad oauth signature
        oauth_string = self._create_oauth_signature(key, "some bad secret", url)
        web.ctx.environ['HTTP_AUTHORIZATION'] = "OAuth %s" % oauth_string
        retval = self.admin_only('somevalue', 'baz')
        self.assertNotEquals(retval, 'baz')


    def _create_oauth_signature(self, key, secret, url):
        consumer = oauth.Consumer(key=key, secret=secret)
        token = oauth.Token(key, secret)
        #    def from_consumer_and_token(cls, consumer, token=None,
        #    http_method=HTTP_METHOD, http_url=None, parameters=None):

        request = oauth.Request.from_consumer_and_token(consumer,
                                                        http_method="GET",
                                                        http_url=url)

        request.sign_request(oauth.SignatureMethod_HMAC_SHA1(), consumer, None)
        oauth_string = ""
        for key in request.keys():
            print "k,v: (%s,%s)" % (key, request[key])
            oauth_string = ("%s=\"%s\", " % (key, request[key])) + oauth_string
        oauth_string = oauth_string[:-2]
        return oauth_string


if __name__ == '__main__':
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.ERROR)
    unittest.main()

