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

if __name__ == "__main__":
    unittest.main()
