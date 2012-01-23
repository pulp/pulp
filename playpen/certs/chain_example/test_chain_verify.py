#!/usr/bin/env python

import unittest
from M2Crypto import X509

CA_CHAIN="certs/ca_chain"
ROOT_CA="certs/ROOT_CA/root_ca.pem"
SUB_CA="certs/SUB_CA/sub_ca.pem"
TEST_CERT="certs/test_cert.pem"


class ChainVerifyTestCase(unittest.TestCase):

    def test_data_is_valid(self):
        root_ca = X509.load_cert(ROOT_CA)
        self.assertTrue(root_ca.check_ca())

        sub_ca = X509.load_cert(SUB_CA)
        self.assertTrue(sub_ca.check_ca())

        test_cert = X509.load_cert(TEST_CERT)
        self.assertFalse(test_cert.check_ca())

    def test_verify_with_missing_sub_CA(self):
        root_ca = X509.load_cert(ROOT_CA)
        test_cert = X509.load_cert(TEST_CERT)

        store = X509.X509_Store()
        store.add_x509(root_ca)
        store_ctx = X509.X509_Store_Context()
        store_ctx.init(store, test_cert)
        self.assertFalse(store_ctx.verify_cert())

    def test_verify_with_missing_root_CA(self):
        sub_ca = X509.load_cert(SUB_CA)
        test_cert = X509.load_cert(TEST_CERT)

        store = X509.X509_Store()
        store.add_x509(sub_ca)
        store_ctx = X509.X509_Store_Context()
        store_ctx.init(store, test_cert)
        self.assertFalse(store_ctx.verify_cert())

    def test_verify_with_full_chain(self):
        root_ca = X509.load_cert(ROOT_CA)
        sub_ca = X509.load_cert(SUB_CA)
        test_cert = X509.load_cert(TEST_CERT)

        store = X509.X509_Store()
        store.add_x509(root_ca)
        store.add_x509(sub_ca)
        store_ctx = X509.X509_Store_Context()
        store_ctx.init(store, test_cert)
        self.assertTrue(store_ctx.verify_cert())

    def test_with_single_chain_file(self):
        test_cert = X509.load_cert(TEST_CERT)
        store = X509.X509_Store()
        self.assertEquals(store.load_info(CA_CHAIN), 1)
        store_ctx = X509.X509_Store_Context()
        store_ctx.init(store, test_cert)
        self.assertTrue(store_ctx.verify_cert())

    def test_with_incomplete_chain_file(self):
        test_cert = X509.load_cert(TEST_CERT)
        store = X509.X509_Store()
        self.assertEquals(store.load_info(SUB_CA), 1)
        store_ctx = X509.X509_Store_Context()
        store_ctx.init(store, test_cert)
        self.assertFalse(store_ctx.verify_cert())

    def load_certs(self, bio, certs=None):
        if not certs:
            certs = []
        try:
            cert = X509.load_cert_bio(bio)
            certs.append(cert)
            return self.load_certs(bio, certs)
        except X509.X509Error, e:
            return certs

    def load_chain_from_string(self, data):
        """
        @param data: A single string of concatenated X509 Certificates in PEM format
        @type data: str
        """
        # Refer to OpenSSL crypto/x509/by_file.c
        # Function: X509_load_cert_file() to see how they parse a chain file and add
        # the certificates to a X509_Store.  Below follows a similar procedure.

        from M2Crypto import BIO
        bio = BIO.MemoryBuffer(data)
        certs = []
        try:
            while True:
                # Read one cert at a time, 'bio' stores the last location read
                # Exception is raised when no more cert data is available
                cert = X509.load_cert_bio(bio)
                if not cert:
                    break
                certs.append(cert)
        except X509.X509Error, e:
            # This is the normal return path.
            # X509.load_cert_bio will throw an exception after reading all of the cert
            # data
            return certs
        return certs


    def test_load_chain_empty(self):
        certs = self.load_chain_from_string("")
        self.assertEquals(len(certs), 0)

        certs = self.load_chain_from_string(None)
        self.assertEquals(len(certs), 0)

    def test_load_chain_malformed(self):
        certs = self.load_chain_from_string("BAD_DATA")
        self.assertEquals(len(certs), 0)

    def test_load_chain(self):
        data = open(CA_CHAIN).read()
        certs = self.load_chain_from_string(data)
        self.assertEquals(len(certs), 2)

        data = open(SUB_CA).read()
        certs = self.load_chain_from_string(data)
        self.assertEquals(len(certs), 1)

        data = open(TEST_CERT).read()
        certs = self.load_chain_from_string(data)
        self.assertEquals(len(certs), 1)

    def test_chain_verify_from_string(self):
        data = open(CA_CHAIN).read()
        ca_chain = self.load_chain_from_string(data)
        test_cert = X509.load_cert(TEST_CERT)

        store = X509.X509_Store()
        for ca in ca_chain:
            store.add_x509(ca)
        store_ctx = X509.X509_Store_Context()
        store_ctx.init(store, test_cert)
        self.assertTrue(store_ctx.verify_cert())

    def test_incomplete_chain_verify_from_string(self):
        data = open(SUB_CA).read()
        ca_chain = self.load_chain_from_string(data)
        test_cert = X509.load_cert(TEST_CERT)

        store = X509.X509_Store()
        for ca in ca_chain:
            store.add_x509(ca)
        store_ctx = X509.X509_Store_Context()
        store_ctx.init(store, test_cert)
        self.assertFalse(store_ctx.verify_cert())

if __name__ == "__main__":
    unittest.main()
