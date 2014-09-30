"""
This module contains tests for the pulp.server.common.openssl module.
"""
import subprocess
import unittest

import mock

from pulp.server.common import openssl


class TestCertificate(unittest.TestCase):
    """
    This class contains tests for the Certificate class.
    """

    def test___init__(self):
        """
        This tests the __init__() method.
        """
        cert_data = 'you can trust me'

        cert = openssl.Certificate(cert_data)

        self.assertEqual(cert._cert, cert_data)
        self.assertEqual(cert._tempdir, None)

    @mock.patch('shutil.rmtree')
    @mock.patch('pulp.server.common.openssl.subprocess.check_call')
    @mock.patch('pulp.server.common.openssl.tempfile.mkdtemp')
    @mock.patch('pulp.server.common.openssl.tempfile.NamedTemporaryFile')
    def test_verify_cert_expired(self, NamedTemporaryFile, mkdtemp, check_call, mock_rmtree):
        """
        Ensure that verify() returns False when the certificate is expired.
        """
        a_tempdir = '/some/dir/'
        cert_filename = '%s%s' % (a_tempdir, 'a.file')

        NamedTemporaryFile.return_value = mock.MagicMock()
        NamedTemporaryFile.return_value.name = cert_filename

        mkdtemp.return_value = a_tempdir

        # This will allow us to simulate the expiration check failing
        check_call.side_effect = subprocess.CalledProcessError(mock.MagicMock(), mock.MagicMock())

        cert_data = "I'm trying to trick you with an expired certificate!"
        ca_chain = ['A CA', 'Another CA']
        cert = openssl.Certificate(cert_data)

        valid = cert.verify(ca_chain)

        # The Certificate should show as invalid
        self.assertEqual(valid, False)
        # mkdtemp should have one call
        mkdtemp.assert_called_once_with()
        # A NamedTemporaryFile should have been created for the Certificate
        NamedTemporaryFile.assert_called_once_with(mode='w', dir=a_tempdir, delete=False)
        # The cert should have been written to the NamedTemporaryFile, and then it should have been
        # closed.
        NamedTemporaryFile.return_value.write.assert_called_once_with(cert_data)
        NamedTemporaryFile.return_value.close.assert_called_once_with()
        # Make sure openssl was called with all the correct args to check expiration
        expected_args = ['openssl', 'x509', '-in', cert_filename, '-noout', '-checkend', '0']
        check_call.assert_called_once_with(expected_args, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE)
        # Cleanup should have happened
        mock_rmtree.assert_called_once_with(a_tempdir)

    @mock.patch('shutil.rmtree')
    @mock.patch('pulp.server.common.openssl.subprocess.check_call')
    @mock.patch('pulp.server.common.openssl.tempfile.mkdtemp')
    @mock.patch('pulp.server.common.openssl.tempfile.NamedTemporaryFile')
    def test_verify_signature_invalid(self, NamedTemporaryFile, mkdtemp, check_call, mock_rmtree):
        """
        Ensure that verify() returns False when the signature is invalid.
        """
        a_tempdir = '/some/dir/'
        cert_filename = '%s%s' % (a_tempdir, 'a.crt')
        ca_filename = '%s%s' % (a_tempdir, 'ca.pack')

        fake_filenames = [cert_filename, ca_filename]
        fake_files = []
        def fake_NamedTemporaryFile(mode, dir, delete):
            fake_file = mock.MagicMock()
            fake_file.name = fake_filenames.pop(0)
            fake_files.append(fake_file)
            return fake_file
        NamedTemporaryFile.side_effect = fake_NamedTemporaryFile

        mkdtemp.return_value = a_tempdir

        # The first time should succeed, the second time should error (simulating openssl failing
        # the signature check).
        check_call_side_effects = [None, subprocess.CalledProcessError(mock.MagicMock(),
                                                                       mock.MagicMock())]
        def fake_check_call(*args, **kwargs):
            """
            Does nothing the first time it is called, and then raises CalledProcessError the second
            time to simulate the certificate check failing.
            """
            what_to_do = check_call_side_effects.pop(0)
            if what_to_do:
                raise what_to_do
        # This will allow us to simulate the expiration check failing
        check_call.side_effect = fake_check_call

        cert_data = "I'm trying to trick you with an expired certificate!"
        ca_chain = [openssl.Certificate(c) for c in ['A CA', 'Another CA']]
        cert = openssl.Certificate(cert_data)

        valid = cert.verify(ca_chain)

        # The Certificate should show as invalid
        self.assertEqual(valid, False)
        # mkdtemp should have one call
        mkdtemp.assert_called_once_with()
        # Two NamedTemporaryFiles should have been created. One for the Certificate, and one for the
        # CA pack.
        self.assertEqual(NamedTemporaryFile.call_count, 2)
        self.assertEqual(NamedTemporaryFile.mock_calls[0][2],
                         {'mode': 'w', 'dir': a_tempdir, 'delete': False})
        self.assertEqual(NamedTemporaryFile.mock_calls[1][2],
                         {'mode': 'w', 'dir': a_tempdir, 'delete': False})
        # The cert should have been written to the first NamedTemporaryFile, and then it should
        # have been closed.
        fake_files[0].write.assert_called_once_with(cert_data)
        fake_files[0].close.assert_called_once_with()
        # The CA pack should have been written to the second NamedTemporaryFile, and then it should
        # have been closed.
        fake_files[1].write.assert_called_once_with('A CA\nAnother CA')
        fake_files[1].close.assert_called_once_with()
        # check_call should have been called twice this time, once to check expiration and once to
        # check signature.
        self.assertEqual(check_call.call_count, 2)
        # Make sure openssl was called with all the correct args to check expiration
        expected_args = ['openssl', 'x509', '-in', cert_filename, '-noout', '-checkend', '0']
        self.assertEqual(check_call.mock_calls[0][1], (expected_args,))
        self.assertEqual(check_call.mock_calls[0][2],
                         {'stdout': subprocess.PIPE, 'stderr': subprocess.PIPE})
        # Make sure openssl was called with all the correct args to check signature
        expected_args = ['openssl', 'verify', '-CAfile', ca_filename, '-purpose', 'sslclient',
                         cert_filename]
        self.assertEqual(check_call.mock_calls[1][1], (expected_args,))
        self.assertEqual(check_call.mock_calls[1][2],
                         {'stdout': subprocess.PIPE, 'stderr': subprocess.PIPE})
        # Cleanup should have happened
        mock_rmtree.assert_called_once_with(a_tempdir)

    @mock.patch('shutil.rmtree')
    @mock.patch('pulp.server.common.openssl.subprocess.check_call')
    @mock.patch('pulp.server.common.openssl.tempfile.mkdtemp')
    @mock.patch('pulp.server.common.openssl.tempfile.NamedTemporaryFile')
    def test_verify_valid(self, NamedTemporaryFile, mkdtemp, check_call, mock_rmtree):
        """
        Ensure that verify() returns True when the client certificate is legitimate.
        """
        a_tempdir = '/some/dir/'
        cert_filename = '%s%s' % (a_tempdir, 'a.crt')
        ca_filename = '%s%s' % (a_tempdir, 'ca.pack')

        fake_filenames = [cert_filename, ca_filename]
        fake_files = []
        def fake_NamedTemporaryFile(mode, dir, delete):
            fake_file = mock.MagicMock()
            fake_file.name = fake_filenames.pop(0)
            fake_files.append(fake_file)
            return fake_file
        NamedTemporaryFile.side_effect = fake_NamedTemporaryFile

        mkdtemp.return_value = a_tempdir

        cert_data = "I am a real cert!"
        ca_chain = [openssl.Certificate('A CA')]
        cert = openssl.Certificate(cert_data)

        valid = cert.verify(ca_chain)

        # The Certificate should show as valid
        self.assertEqual(valid, True)
        # mkdtemp should have one call
        mkdtemp.assert_called_once_with()
        # Two NamedTemporaryFiles should have been created. One for the Certificate, and one for the
        # CA pack.
        self.assertEqual(NamedTemporaryFile.call_count, 2)
        self.assertEqual(NamedTemporaryFile.mock_calls[0][2],
                         {'mode': 'w', 'dir': a_tempdir, 'delete': False})
        self.assertEqual(NamedTemporaryFile.mock_calls[1][2],
                         {'mode': 'w', 'dir': a_tempdir, 'delete': False})
        # The cert should have been written to the first NamedTemporaryFile, and then it should
        # have been closed.
        fake_files[0].write.assert_called_once_with(cert_data)
        fake_files[0].close.assert_called_once_with()
        # The CA pack should have been written to the second NamedTemporaryFile, and then it should
        # have been closed.
        fake_files[1].write.assert_called_once_with('A CA')
        fake_files[1].close.assert_called_once_with()
        # check_call should have been called twice this time, once to check expiration and once to
        # check signature.
        self.assertEqual(check_call.call_count, 2)
        # Make sure openssl was called with all the correct args to check expiration
        expected_args = ['openssl', 'x509', '-in', cert_filename, '-noout', '-checkend', '0']
        self.assertEqual(check_call.mock_calls[0][1], (expected_args,))
        self.assertEqual(check_call.mock_calls[0][2],
                         {'stdout': subprocess.PIPE, 'stderr': subprocess.PIPE})
        # Make sure openssl was called with all the correct args to check signature
        expected_args = ['openssl', 'verify', '-CAfile', ca_filename, '-purpose', 'sslclient',
                         cert_filename]
        self.assertEqual(check_call.mock_calls[1][1], (expected_args,))
        self.assertEqual(check_call.mock_calls[1][2],
                         {'stdout': subprocess.PIPE, 'stderr': subprocess.PIPE})
        # Cleanup should have happened
        mock_rmtree.assert_called_once_with(a_tempdir)
