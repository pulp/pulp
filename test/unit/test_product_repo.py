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
import unittest

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.repo import RepoApi

CERT_FILE="/certs/nimbus_cloude_debug.crt"
CERT_KEY="/certs/nimbus_cloude_debug.key"
CA_CERT="/certs/cdn.redhat.com-chain.crt"

import testutil

logging.root.setLevel(logging.ERROR)

class TestProductRepo(unittest.TestCase):

    def clean(self):
        self.rapi.clean()
        
    def setUp(self):
        self.config = testutil.load_test_config()
        self.rapi = RepoApi()
        self.clean()
        
    def tearDown(self):
        self.clean()
        
    def test_create_product_repo(self):
        content_set = {
            "rhel-server" : "/content/dist/rhel/server/$releasever/$basearch/os"}
        try:
            cert_data = {'ca' : open(CA_CERT, "rb").read(),
                         'cert' : open(CERT_FILE, "rb").read(),
                         'key' : open(CERT_KEY, 'rb').read()}
            self.rapi.create_product_repo(content_set, cert_data, productid="test-product")
            repos = self.rapi.get_repo_by_product("test-product")
            self.assertTrue(len(repos) > 0)
        except IOError, ie:
            print("IOError:: Make sure the certificates paths are readable %s" % ie)
            

if __name__ == '__main__':
    unittest.main()

