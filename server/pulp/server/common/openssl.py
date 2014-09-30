"""
OpenSSL wrapper.
"""
import os
import shutil
import subprocess
import tempfile


class Certificate(object):
    """
    OpenSSL x.509 certificate
    """

    def __init__(self, pem):
        """
        :param pem: A PEM encoded certificate.
        :type  pem: str
        """
        self._cert = pem
        self._tempdir = None

    def verify(self, ca_chain):
        """
        Verify the certificate. This function will ensure that the Certificate is not expired, and
        that it is signed by at least one of the CAs in the ca_chain. It will return True if it is
        valid, and False otherwise.

        :param ca_chain: A list of CA certificates. Each should be a Certificate object.
        :type  ca_chain: iterable
        :return:         True if verified.
        :rtype:          bool
        """
        # We must be sure to cleanup no matter what happens
        try:
            self._tempdir = tempfile.mkdtemp()

            # Write the cert to a tempfile
            cert = tempfile.NamedTemporaryFile(mode='w', dir=self._tempdir, delete=False)
            cert.write(self._cert)
            cert.close()

            # Check to make sure the client cert is not expired
            args = ['openssl', 'x509', '-in', cert.name, '-noout', '-checkend', '0']
            try:
                subprocess.check_call(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError:
                # The certificate is expired
                return False

            # Write the CAs to a tempfile
            ca = tempfile.NamedTemporaryFile(mode='w', dir=self._tempdir, delete=False)
            ca_chain = [c._cert for c in ca_chain]
            ca.write('\n'.join(ca_chain))
            ca.close()

            # Now let's check to make sure the certificate is signed by one of our trusted CAs
            args = ['openssl', 'verify', '-CAfile', ca.name, '-purpose', 'sslclient', cert.name]
            try:
                subprocess.check_call(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError:
                # The certificate is not signed by a trusted CA
                return False

            # If we've survived the above carnage, this cert is legit
            return True
        finally:
            # Make sure we always clean up
            if self._tempdir:
                shutil.rmtree(self._tempdir)
                self._tempdir = None
