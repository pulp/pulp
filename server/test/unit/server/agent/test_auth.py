# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
from unittest import TestCase
from ConfigParser import ConfigParser
from StringIO import StringIO

from mock import patch, Mock
from M2Crypto import RSA, BIO
from gofer.messaging.auth import ValidationFailed

from pulp.server.agent.auth import Authenticator


RSA_KEY = """
-----BEGIN RSA PRIVATE KEY-----
MIICWwIBAAKBgQDbZu3/ml//XLdb+n8fMklr3CkpBYfIqYFGQzcfDyIBGJUrWZRQ
gwkQn2P9J8QgVyNSrByFN1DbEJvrY9Lo6kzqy8flh9Ws1GKMRfqJZk99/Zae/Wbn
9dQqa9EYrMZR3pO5UMmpSRFzZNTWEvmP4WAP4fque1VQJiUwXnMkTSO7cQIDAQAB
AoGAQdtrpUXZevWBtIJElkCp+U5krIOUdo8q1sRmT1RjiKCwZgrFkkVC+1Jc2SiO
noaJe89d4D7ybk9V/hpAvNlXrLSc+Gaq8xEOITiiAE1G09Ojc9Q0SFxhW9Sugq/T
dw44QSxA2wJ8zo9nImwKAEAzt6lDOaCQ2qZrZFkSUSYbboECQQDytgjrK9FsrMSF
yz88UCPOo6BLNoXoDgN5SKWEPn+Q3hz+qRy6ka9YDUaxx19C0jiZRAYeg96Zh2MG
CAWWfRCVAkEA52ovBITgWaPYHJcSlIK4rkgpYnD5atLZuajwhnWeBQ0sPhy06CNO
Cp+PIVIYVWtHcmxJk1aOFYsG29G9rg38bQJAMLI/Ndfzy8caIvH1fQdjN8lylsSY
t0dggQwHUXIsrAc0cA/EGNa0BImdXnvu6/w7qNySEbtJhSo5vvMLE/eBxQJATm9y
EkELXban+EDIPmf0OrYguMn779YZj9EP/TL+ZU3qsf6+3nOg7v7X335Y2xLqe4Dy
iyrqK6kcoQL9HHKHHQJAT5jTKawl830Zx85t/j42NNhHsMyXXgtmz4lYyhb/UCik
8vRK7LSjxYvCgnFT+wXT9hOjfEW+AnOKYJTHai4BNw==
-----END RSA PRIVATE KEY-----
"""

OTHER_KEY = """
-----BEGIN RSA PRIVATE KEY-----
MIICXQIBAAKBgQDcx31TTh+mcm7v3NtQrkfHL5KgRXv7uDCLI56vULYSp5HtC9F9
Jph2DT8l/XVXj0L5WMPP12VRZkmmgR9LDF5iHXnWE47Dy/6Midz4KIV1Vx7O/LdX
btzq0lYRcaEofZPSfapf7hpNMhl3G5ioUvXp6vbh9EbGLetdXeVeqii53QIDAQAB
AoGBAMiLBJIJIsLEq3SB/01YIacS1XNz6l0KQD4DCv9gpyJmyCy0UYQG7PI+sh/G
DTKN1V49fRBsLYI1Ea2HGG/JOmjhQOxjz/F1jAMbQfeTXhu/JVYlhDgOK3nC+DnF
jmJ2FfqUxr/eE87IzUF5Qm4TVffKwCSaxQ3u3xkbk9+oBkMBAkEA8OVxcTyKmgho
9hk0PHPuFIeWAgKf5015oLUZPPeYYeACiZGUnvP1BdiO9QpZyIPaEiySDb2jv0ZR
kJpHW7qpPQJBAOqfJ3Q+6v/u9pKmjcH8kEtIB8Mtnm5WIs4cLhlChI4xbm1Gawvp
Lly6GSNUvsFVxyaMrqaMQxtKdHg4MtZxHSECQBpVOn1iXNRRrweX4bnqAlCEMcWu
e8RRF8aVhVjAyAuK7TwUieaGTHaDIb1vkDj3ENODw8N0w32ZNjlUZBCG6xECQETP
ms2wKlIXrr+CE69iOJurq4Ml3QJ1Rs32W9rStHfTrZRlA75BjHRrrDW9hBjF5Ju8
xPhZyNC3PIOJz/cuw6ECQQCbfqV4YWiW0j2t/dotJjA0S/QdQYJcUbo/kNUar65v
ZdgAs+Krt4gDkn34BF5009pZf0IBANSPMeqvw4BWr3G4
-----END RSA PRIVATE KEY-----
"""

RSA_PUB = """
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDbZu3/ml//XLdb+n8fMklr3Ckp
BYfIqYFGQzcfDyIBGJUrWZRQgwkQn2P9J8QgVyNSrByFN1DbEJvrY9Lo6kzqy8fl
h9Ws1GKMRfqJZk99/Zae/Wbn9dQqa9EYrMZR3pO5UMmpSRFzZNTWEvmP4WAP4fqu
e1VQJiUwXnMkTSO7cQIDAQAB
-----END PUBLIC KEY-----
"""

TEST_CONF = """
[authentication]
rsa_key: /etc/pki/pulp/rsa.key

[messaging]
auth_enabled: true
"""

PULP_CONF = ConfigParser()
PULP_CONF.readfp(StringIO(TEST_CONF))


class TestAuthentication(TestCase):

    @patch('__builtin__.open')
    @patch('pulp.server.agent.auth.pulp_conf', PULP_CONF)
    def test_load(self, mock_open):
        mock_fp = Mock()
        mock_fp.read = Mock(return_value=RSA_KEY)
        mock_fp.__enter__ = Mock(return_value=mock_fp)
        mock_fp.__exit__ = Mock()
        mock_open.return_value = mock_fp

        # test

        authenticator = Authenticator()
        authenticator.load()

        # validation

        self.assertTrue(mock_fp.__exit__.called)
        self.assertTrue(isinstance(authenticator.rsa_key, RSA.RSA))

    @patch('pulp.server.agent.auth.pulp_conf', PULP_CONF)
    @patch('pulp.server.managers.factory.consumer_manager')
    def test_key(self, mock_factory):
        consumer_id = 'test-consumer'
        mock_manager = Mock()
        mock_manager.get_consumer = Mock(return_value={'rsa_pub': RSA_PUB})
        mock_factory.return_value = mock_manager

        # test

        key = Authenticator.get_key(consumer_id)

        # validation

        self.assertTrue(isinstance(key, RSA.RSA))

    def test_signing(self):
        message = 'hello'
        key = RSA.load_key_bio(BIO.MemoryBuffer(RSA_KEY))

        # test
        authenticator = Authenticator()
        authenticator.rsa_key = key
        signature = authenticator.sign(message)

        #validation

        self.assertEqual(signature, key.sign(message))

    def test_signing_not_enabled(self):
        authenticator = Authenticator()
        authenticator.enabled = False
        signature = authenticator.sign('hello')
        self.assertEqual(signature, '')

    @patch('pulp.server.agent.auth.Authenticator.get_key')
    def test_validated(self, mock_get):
        message = 'hello'
        consumer_id = 'test-consumer_id'
        document = Mock()
        document.any = {'consumer_id': consumer_id}
        key = RSA.load_key_bio(BIO.MemoryBuffer(RSA_KEY))

        mock_get.return_value = RSA.load_pub_key_bio(BIO.MemoryBuffer(RSA_PUB))

        # test

        authenticator = Authenticator()
        authenticator.validate(document, message, key.sign(message))
        mock_get.assert_called_with(consumer_id)

    @patch('pulp.server.agent.auth.Authenticator.get_key')
    def test_not_validated(self, mock_get):
        message = 'hello'
        consumer_id = 'test-consumer_id'
        document = Mock()
        document.any = {'consumer_id': consumer_id}
        key = RSA.load_key_bio(BIO.MemoryBuffer(OTHER_KEY))

        mock_get.return_value = RSA.load_pub_key_bio(BIO.MemoryBuffer(RSA_PUB))

        # test

        authenticator = Authenticator()
        self.assertRaises(
            ValidationFailed, authenticator.validate, document, message, key.sign(message))
        mock_get.assert_called_with(consumer_id)

    @patch('pulp.server.agent.auth.Authenticator.get_key')
    def test_validated_not_raised(self, mock_get):
        mock_get.return_value.verify = Mock(return_value=False)
        consumer_id = 'test-consumer_id'
        document = Mock()
        document.any = {'consumer_id': consumer_id}

        # test

        authenticator = Authenticator()
        self.assertRaises(ValidationFailed, authenticator.validate, document, '', '')
        mock_get.assert_called_with(consumer_id)

    def test_validate_not_enabled(self):
        authenticator = Authenticator()
        authenticator.enabled = False
        authenticator.validate('', '', '')
