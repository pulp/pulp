from cStringIO import StringIO
import unittest

from pulp.plugins.util import verification
from pulp.server import util


class VerificationTests(unittest.TestCase):

    def test_size(self):
        # Setup
        expected_size = 9
        test_file = StringIO('Test data')

        # Test - Should not raise an exception
        verification.verify_size(test_file, expected_size)

    def test_size_incorrect(self):
        test_file = StringIO('Test data')

        # Test
        self.assertRaises(verification.VerificationException, verification.verify_size, test_file,
                          1)

    def test_checksum_sha1(self):
        # Setup
        test_file = StringIO('Test Data')
        expected_checksum = 'cae99c6102aa3596ff9b86c73881154e340c2ea8'

        # Test - Should not raise an exception
        verification.verify_checksum(test_file, util.TYPE_SHA1, expected_checksum)

    def test_checksum_sha(self):
        # Setup (sha is an alias for sha1)
        test_file = StringIO('Test Data')
        expected_checksum = 'cae99c6102aa3596ff9b86c73881154e340c2ea8'

        # Test - Should not raise an exception
        verification.verify_checksum(test_file, util.TYPE_SHA, expected_checksum)

    def test_checksum_sha256(self):
        # Setup
        test_file = StringIO('Test data')
        expected_checksum = 'e27c8214be8b7cf5bccc7c08247e3cb0c1514a48ee1f63197fe4ef3ef51d7e6f'

        # Test - Should not raise an exception
        verification.verify_checksum(test_file, util.TYPE_SHA256, expected_checksum)

    def test_checksum_sha256_incorrect(self):
        # Setup
        test_file = StringIO('Test data')

        # Test
        self.assertRaises(verification.VerificationException, verification.verify_checksum,
                          test_file, util.TYPE_SHA256, 'foo')

    def test_checksum_invalid_checksum(self):
        self.assertRaises(util.InvalidChecksumType, verification.verify_checksum,
                          StringIO(), 'fake-type', 'irrelevant')
