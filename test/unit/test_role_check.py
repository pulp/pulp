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
import sys
import os
import unittest
import logging
import web

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

import testutil

from pulp.webservices.runtime import bootstrap
bootstrap(testutil.load_test_config())

from pulp.api.user import UserApi
from pulp.certificate import Certificate
from pulp.webservices.role_check import RoleCheck
from ConfigParser import ConfigParser

logging.root.addHandler(logging.StreamHandler())
logging.root.setLevel(logging.DEBUG)



class TestRoleCheck(unittest.TestCase):

    def setUp(self):
        self.config = testutil.load_test_config()
        self.uapi = UserApi(self.config)
        
    @RoleCheck(consumer=True)
    def some_method(self, someparam):
        print "We shouldn't be in here"
        return True
        
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
        user = self.uapi.create(login, password=password)
        web.ctx['headers'] = []
        web.ctx['environ'] = dict()
        
        retval = self.some_method('somevalue')
        self.assertTrue(retval)
        
        # Check for bad pass
        loginpass = "%s:%s" % (login, "invalid password")
        encoded = base64.encodestring(loginpass)
        web.ctx.environ['HTTP_AUTHORIZATION'] = "Basic %s" % encoded
        retval = self.some_method('somevalue')
        self.assertTrue(retval != True)
        
        # Check for bad username
        loginpass = "%s:%s" % ("non existing user", password)
        encoded = base64.encodestring(loginpass)
        web.ctx.environ['HTTP_AUTHORIZATION'] = "Basic %s" % encoded
        retval = self.some_method('somevalue')
        self.assertTrue(retval != True)
        
        
         

if __name__ == '__main__':
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.ERROR)
    unittest.main()
