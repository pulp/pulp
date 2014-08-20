"""
OpenSSL (libcrypto) wrapper.
"""

from ctypes import CDLL
from ctypes.util import find_library
from ctypes import c_char_p


openssl = CDLL(find_library('crypto'))


class Store(object):
    """
    OpenSSL certificate store.
    :ivar ptr: A pointer to the C structure.
    :type ptr: X509_STORE
    """

    def __init__(self):
        self.ptr = openssl.X509_STORE_new()

    def add(self, certificate):
        """
        Add a certificate to the store.
        :param certificate: The certificate to add.
        :type certificate: Certificate
        """
        openssl.X509_STORE_add_cert(self.ptr, certificate.ptr)

    def __del__(self):
        openssl.X509_STORE_free(self.ptr)


class StoreContext(object):
    """
    OpenSSL certificate store context.
    :ivar ptr: A pointer to the C structure.
    :type ptr: X509_STORE_CTX
    """

    def __init__(self, store, certificate):
        """
        :param store: A certificate store.
        :type store: Store
        :param certificate: Used to initialize the context.
        :type certificate: Certificate
        """
        self.ptr = openssl.X509_STORE_CTX_new()
        openssl.X509_STORE_CTX_init(self.ptr, store.ptr, certificate.ptr, None)

    def __del__(self):
        openssl.X509_STORE_CTX_free(self.ptr)


class Certificate(object):
    """
    OpenSSL x.509 certificate
    :ivar ptr: A pointer to the C structure.
    :type ptr: X509
    """

    def __init__(self, pem):
        """
        :param pem: A PEM encoded certificate.
        :type pem: str
        """
        bio = openssl.BIO_new_mem_buf(c_char_p(pem), len(pem))
        self.ptr = openssl.PEM_read_bio_X509(bio, None, 0, None)
        openssl.BIO_free(bio)

    def verify(self, ca_chain):
        """
        Verify the certificate.
        :param ca_chain: A list of CA certificates.
        :type ca_chain: iterable
        :return: True if verified.
        :rtype: bool
        """
        store = Store()
        for ca in ca_chain:
            store.add(ca)
        ctx = StoreContext(store, self)
        retval = openssl.X509_verify_cert(ctx.ptr)
        return retval == 1

    def __del__(self):
        openssl.X509_free(self.ptr)
