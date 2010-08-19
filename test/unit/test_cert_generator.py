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
#

import logging
import os
import sys
import unittest

srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src"
sys.path.insert(0, srcdir)

from pulp.server.certificate import Certificate
import pulp.server.cert_generator as cert_generator

class TestCertGeneration(unittest.TestCase):

    def test_generation(self):
        cid = "foobarbaz"
        pem = cert_generator._make_priv_key()
        self.assertTrue(pem.startswith('-----BEGIN RSA PRIVATE KEY-----'))
        (pk, x509_pem) = cert_generator.make_cert(cid)
        print "CERT!: %s" % x509_pem
        self.assertTrue(pk is not None)
        self.assertTrue(x509_pem is not None)
        cert = Certificate()
        cert.update(str(x509_pem))
        subject = cert.subject()
        consumer_cert_uid = subject.get('CN', None)
        self.assertEqual(cid, consumer_cert_uid)
        

if __name__ == '__main__':
    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(logging.INFO)
    unittest.main()
