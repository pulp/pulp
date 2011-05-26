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

import os
import unittest

from pulp.client.connection import Restlib

class TestApi(unittest.TestCase):
    
    def test_cert_validation(self):
        my_dir = os.path.abspath(os.path.dirname(__file__))
        keypath = my_dir + '/../unit/data/test_key.pem'
        certpath = my_dir + '/../unit/data/test_cert.pem'
        
        failed = False
        out = None
        try:
            rl = Restlib('localhost', 443, '/test/invalid-id/', 
                         cert_file=certpath, key_file=keypath)
            out = rl.request_get('auth/')
        except Exception, e:
            failed = True
        self.assertTrue(failed)
        self.assertTrue(out == None)
         
        rl = Restlib('localhost', 443, '/test/fb12d975-1f33-4b34-8ac9-0adb6089fb87/', 
             cert_file=certpath, key_file=keypath)
        out = rl.request_get('auth/')
        print "Valid request output: %s" % out
        self.assertTrue(out != None)
        
        



