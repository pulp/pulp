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
import os
import sys
import unittest

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"

sys.path.insert(0, srcdir)
commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'

sys.path.insert(0, commondir)

from pulp.server.api.cds import CdsApi
from pulp.server.pexceptions import PulpException

class TestCdsApi(unittest.TestCase):

    def setUp(self):
        self.cds_api = CdsApi()

    def tearDown(self):
        self.cds_api.clean()

    def test_register_simple_attributes(self):
        '''
        Tests the register call with only the required arguments.
        '''

        # Test
        self.cds_api.register('cds.example.com')

        # Verify
        cds = self.cds_api.cds('cds.example.com')
        self.assertTrue(cds is not None)
        self.assertEqual(cds['hostname'], 'cds.example.com')
        self.assertEqual(cds['name'], 'cds.example.com')
        self.assertEqual(cds['description'], None)

    def test_register_full_attributes(self):
        '''
        Tests the register call specifying a value for all optional arguments.
        '''

        # Test
        self.cds_api.register('cds.example.com', name='Test CDS', description='Test CDS Description')

        # Verify
        cds = self.cds_api.cds('cds.example.com')
        self.assertTrue(cds is not None)

        self.assertEqual(cds['hostname'], 'cds.example.com')
        self.assertEqual(cds['name'], 'Test CDS')
        self.assertEqual(cds['description'], 'Test CDS Description')

    def test_register_no_hostname(self):
        '''
        Tests the error condition where register is called without a hostname.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_api.register, None)

    def test_register_already_exists(self):
        '''
        Tests the error condition where a CDS already exists with the given hostname.
        '''

        # Setup
        self.cds_api.register('cds.example.com')

        # Test
        self.assertRaises(PulpException, self.cds_api.register, 'cds.example.com')

    def test_unregister(self):
        '''
        Tests the basic case where unregister is successful.
        '''

        # Setup
        self.cds_api.register('cds.example.com')
        cds = self.cds_api.cds('cds.example.com')
        self.assertTrue(cds is not None)

        # Test
        self.cds_api.unregister('cds.example.com')

        # Verify
        cds = self.cds_api.cds('cds.example.com')
        self.assertTrue(cds is None)

    def test_unregister_no_hostname(self):
        '''
        Tests the error condition where unregister is called without a hostname.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_api.unregister, None)

    def test_unregister_invalid_hostname(self):
        '''
        Tests the error condition where the given hostname does not correspond to an existing
        CDS.
        '''

        # Test
        self.assertRaises(PulpException, self.cds_api.unregister, 'foo.example.com')

    def test_cds_lookup_successful(self):
        '''
        Tests the CDS lookup when a CDS exists with the given hostname.
        '''

        # Setup
        self.cds_api.register('findme.example.com')

        # Test
        cds = self.cds_api.cds('findme.example.com')

        # Verify
        self.assertTrue(cds is not None)

    def test_cds_lookup_failed(self):
        '''
        Tests the CDS lookup when no CDS exists with the given hostname conforms to the
        API documentation.
        '''

        # Test
        cds = self.cds_api.cds('fake.example.com')

        # Verify
        self.assertTrue(cds is None)
