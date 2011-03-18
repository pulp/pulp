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
import sys
import os
import unittest

# Pulp
srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

import pulp.server.repo_cert_utils as utils
import testutil


class TestRepoCertUtils(unittest.TestCase):

    def test_validate_cert_bundle_valid(self):
        '''
        Tests that validating a valid cert bundle does not indicate an error.
        '''

        # Setup
        bundle = {'ca' : 'PEM', 'cert' : 'PEM', 'key' : 'PEM'}

        # Test
        utils.validate_cert_bundle(bundle) # should not throw an error

    def test_validate_cert_bundle_missing_keys(self):
        '''
        Tests that a cert bundle missing any of the required keys indicates
        an error.
        '''

        # Test missing CA
        self.assertRaises(ValueError, utils.validate_cert_bundle, {'cert' : 'PEM', 'key' : 'PEM'})
        self.assertRaises(ValueError, utils.validate_cert_bundle, {'ca' : 'PEM', 'key' : 'PEM'})
        self.assertRaises(ValueError, utils.validate_cert_bundle, {'ca' : 'PEM', 'cert' : 'PEM'})

    def test_validate_cert_bundle_non_dict(self):
        '''
        Tests that calling validate without passing a dict correctly indicates
        an error.
        '''

        # Test bad parameter
        self.assertRaises(ValueError, utils.validate_cert_bundle, 'foo')

    def test_validate_cert_bundle_none(self):
        '''
        Tests that calling validate with None throws the correct error.
        '''

        # Test missing parameter
        self.assertRaises(ValueError, utils.validate_cert_bundle, None)

    def test_validate_cert_bundle_extra_keys(self):
        '''
        Tests that calling validate with non-cert bundle keys raises an error.
        '''

        # Setup
        bundle = {'ca' : 'PEM', 'cert' : 'PEM', 'key' : 'PEM', 'foo' : 'bar'}

        # Test
        self.assertRaises(ValueError, utils.validate_cert_bundle, bundle)
        