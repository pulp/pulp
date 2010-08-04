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
import logging
import sys
import os
import time
import unittest
import uuid

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

from pulp.api.user import UserApi
from pulp.model import User
from pulp.util import random_string
from pulp.certificate import Certificate

from ConfigParser import ConfigParser

import testutil


class TestUsers(unittest.TestCase):

    def clean(self):
        self.uapi.clean()
        
    def setUp(self):
        self.config = testutil.load_test_config()
        self.uapi = UserApi()
        self.clean()
        
    def tearDown(self):
        self.clean()
        
    def test_create(self):
        clear_txt_pass = 'some password'
        user = self.uapi.create('login-test', id=str(uuid.uuid4()), 
                                password=clear_txt_pass,
                                name='Fred Franklin') 
        self.assertTrue(user != None)
        user = self.uapi.user('login-test')
        self.assertTrue(user != None)
        self.assertNotEqual(clear_txt_pass, user['password'])

    def test_default_admin(self):
        """
        Check to make sure we always have an admin user
        """
        default_login = self.config.get('server', 'default_login')
        admin = self.uapi.user(default_login)
        self.assertTrue(admin != None)
        
    def test_duplicate(self):
        id = uuid.uuid4()
        login = 'dupe-test'
        user = self.uapi.create(login, id)
        try:
            user = self.uapi.create(login, id)
            raise Exception, 'Duplicate allowed'
        except:
            pass
        
    def test_user_list(self):
        user = self.uapi.create('login-test')
        users = self.uapi.users()
        assert(len(users) == 2)
        
    def test_clean(self):
        user = self.uapi.create('login-test')
        self.uapi.clean()
        users = self.uapi.users()
        assert(len(users) == 1)
        
    def test_delete(self):
        login = 'some-login'
        user = self.uapi.create(login)
        self.uapi.delete(login=login)
        user = self.uapi.user(login)
        assert(user is None)
        
        
if __name__ == '__main__':
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.ERROR)
    unittest.main()
