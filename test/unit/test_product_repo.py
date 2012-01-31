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

# Python
import logging
import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)) + "/../common/")
import testutil

from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.repo import RepoApi

CERT_FILE = "/certs/nimbus_cloude_debug.crt"
CERT_KEY = "/certs/nimbus_cloude_debug.key"
CA_CERT = "/certs/cdn.redhat.com-chain.crt"

logging.root.setLevel(logging.ERROR)

class TestProductRepo(testutil.PulpAsyncTest):

    def test_create_product_repo(self):
        content_set = [{
            'content_set_label' : "rhel-server" ,
            'content_rel_url' : "/content/dist/rhel/server/$releasever/$basearch/os"},]
        try:
            cert_data = {'ca' : open(CA_CERT, "rb").read(),
                         'cert' : open(CERT_FILE, "rb").read(),
                         'key' : open(CERT_KEY, 'rb').read()}
            self.repo_api.create_product_repo(content_set, cert_data, groupid="test-product")
            repos = self.repo_api.repositories(spec={"groupid" : "test-product"}, fields=["groupid"])
            self.assertTrue(len(repos) > 0)
        except IOError, ie:
            print("IOError:: Make sure the certificates paths are readable %s" % ie)
            
    def test_delete_product_repo(self):
        product_name = "test_product"
        self.repo_api.delete_product_repo(product_name)
        repos = self.repo_api.repositories(spec={"groupid" : "test-product"})
        self.assertTrue(len(repos) == 0)


if __name__ == '__main__':
    unittest.main()

