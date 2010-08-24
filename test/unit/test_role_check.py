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
import unittest
import web

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)


from pulp.server.api.user import UserApi
from pulp.server.api.consumer import ConsumerApi
import pulp.server.auth.cert_generator as cert_generator
from pulp.server.auth.certificate import Certificate
from pulp.server.webservices.role_check import RoleCheck
import testutil
testutil.load_test_config()

class TestRoleCheck(unittest.TestCase):

    def setUp(self):
        self.config = testutil.load_test_config()
        self.uapi = UserApi()
        self.capi = ConsumerApi()

    def tearDown(self):
        self.uapi.clean()
        self.capi.clean()
        
    @RoleCheck(consumer=True)
    def some_method(self, someparam, otherparam):
        print "some method executed"
        return otherparam

    @RoleCheck(admin=True)
    def some_other_method(self, someparam, otherparam):
        print "some_other_method executed"
        return otherparam

    @RoleCheck(admin=True, consumer=True)
    def some_other_method2(self, someparam, otherparam):
        print "some_other_method2 executed"
        return otherparam

    @RoleCheck(admin=True, consumer_id=True)
    def some_other_method3(self, consumer_id, otherparam):
        print "some_other_method3 executed"
        return otherparam

    def test_id_cert(self):
        consumerUid = "some-id-cert-test"
        self.capi.create(consumerUid, "desc")
        (temp_pk, temp_cert) = cert_generator.make_cert(consumerUid)
        self.assertTrue(temp_cert is not None)
        cert = Certificate()
        cert.update(temp_cert)
        web.ctx['headers'] = []
        web.ctx['environ'] = dict()
        web.ctx.environ['SSL_CLIENT_CERT'] = cert.toPEM()
        retval = self.some_method("blippy","baz")
        print "retval %s" % retval
        self.assertEquals(retval, "baz")

        # Test that both the cert + id *in* the cert match
        retval = self.some_other_method3(consumerUid,"baz")
        self.assertEquals(retval, "baz")
        
        # Test the opposite, good cert, bad param
        retval = self.some_other_method3("fake-consumer-uid","baz")
        self.assertNotEquals(retval, "baz")
        
        
        # Test with non-existing consumer
        consumerUid = "non-existing-consumer"
        (temp_pk, temp_cert) = cert_generator.make_cert(consumerUid)
        cert = Certificate()
        cert.update(temp_cert)
        web.ctx.environ['SSL_CLIENT_CERT'] = cert.toPEM()
        retval = self.some_method(consumerUid,"baz")
        print "retval %s" % retval
        self.assertNotEquals(retval, "baz")
        
         
    def test_role_check(self):
        my_dir = os.path.abspath(os.path.dirname(__file__))
        test_cert = my_dir + "/data/test_cert.pem"
        cert = Certificate()
        cert.read(test_cert)
        web.ctx['headers'] = []
        web.ctx['environ'] = dict()
        web.ctx.environ['SSL_CLIENT_CERT'] = cert.toPEM()
        retval = self.some_method('somevalue')
        self.assertTrue(web.ctx.status.startswith('401'))
        
    def test_uname_pass(self):
        # create a user
        login = "test_auth"
        password = "some password"
        self.uapi.create(login, password=password)
        web.ctx['headers'] = []
        web.ctx['environ'] = dict()
        
        # Check we can run the method with no setup in web
        retval = self.some_other_method('somevalue', 'baz')
        self.assertNotEqual(retval, 'baz')
        
        # Check for bad pass
        loginpass = "%s:%s" % (login, "invalid password")
        encoded = base64.encodestring(loginpass)
        web.ctx.environ['HTTP_AUTHORIZATION'] = "Basic %s" % encoded
        retval = self.some_other_method('somevalue', 'baz')
        self.assertNotEqual(retval, 'baz')
        
        # Check for bad username
        loginpass = "%s:%s" % ("non existing user", password)
        encoded = base64.encodestring(loginpass)
        web.ctx.environ['HTTP_AUTHORIZATION'] = "Basic %s" % encoded
        retval = self.some_other_method('somevalue', 'baz')
        self.assertNotEqual(retval, 'baz')
        
        # Check for a proper result
        loginpass = "%s:%s" % (login, password)
        encoded = base64.encodestring(loginpass)
        web.ctx.environ['HTTP_AUTHORIZATION'] = "Basic %s" % encoded
        retval = self.some_other_method('somevalue', 'baz')
        self.assertEquals(retval, 'baz')

        # Check for bad pass
        loginpass = "%s:%s" % (login, "invalid password")
        encoded = base64.encodestring(loginpass)
        web.ctx.environ['HTTP_AUTHORIZATION'] = "Basic %s" % encoded
        retval = self.some_other_method2('somevalue', 'baz')
        self.assertNotEqual(retval, 'baz')
        
        # Check for bad username
        loginpass = "%s:%s" % ("non existing user", password)
        encoded = base64.encodestring(loginpass)
        web.ctx.environ['HTTP_AUTHORIZATION'] = "Basic %s" % encoded
        retval = self.some_other_method2('somevalue', 'baz')
        self.assertNotEqual(retval, 'baz')
        
        # Check for a proper result
        loginpass = "%s:%s" % (login, password)
        encoded = base64.encodestring(loginpass)
        web.ctx.environ['HTTP_AUTHORIZATION'] = "Basic %s" % encoded
        retval = self.some_other_method2('somevalue', 'baz')
        self.assertEquals(retval, 'baz')

    
if __name__ == '__main__':
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.ERROR)
    unittest.main()
