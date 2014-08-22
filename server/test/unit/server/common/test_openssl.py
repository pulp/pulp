
from unittest import TestCase

from mock import patch, Mock

from pulp.server.common.openssl import BIO, Store, StoreContext, Certificate


#
# Note: Tests not explicitly validating __del__() must ensure that mocked
#       lib calls returning pointers, return 0 (NULL).  This prevents
#       __del__() calling free() with random or bogus pointers when post
#       run objects are garbage collected.
#


class TestBIO(TestCase):

    @patch('pulp.server.common.openssl.c_char_p')
    @patch('pulp.server.common.openssl.openssl')
    def test_construction(self, fake_lib, fake_char_p):
        ptr = 0
        c_ptr = 123
        fake_lib.BIO_new_mem_buf.return_value = ptr
        fake_char_p.return_value = c_ptr
        content = 'hello'

        # test
        bio = BIO(content)

        # validation
        fake_char_p.assert_called_with(content)
        fake_lib.BIO_new_mem_buf.assert_called_with(c_ptr, len(content))
        self.assertEqual(bio.ptr, ptr)

    @patch('pulp.server.common.openssl.openssl')
    def test_del(self, fake_lib):
        ptr = 1
        fake_lib.BIO_new_mem_buf.return_value = ptr

        # test
        bio = BIO('')
        bio.__del__()

        # validation
        fake_lib.BIO_free.assert_called_with(ptr)


class TestStore(TestCase):

    @patch('pulp.server.common.openssl.openssl')
    def test_construction(self, fake_lib):
        ptr = 0
        fake_lib.X509_STORE_new.return_value = ptr

        # test
        store = Store()

        # validation
        fake_lib.X509_STORE_new.assert_called_with()
        self.assertEqual(store.ptr, ptr)

    @patch('pulp.server.common.openssl.openssl')
    def test_add(self, fake_lib):
        ptr = 0
        fake_lib.X509_STORE_new.return_value = ptr
        certificate = Mock()

        # test
        store = Store()
        store.add(certificate)

        # validation
        fake_lib.X509_STORE_add_cert.assert_called_with(store.ptr, certificate.ptr)

    @patch('pulp.server.common.openssl.openssl')
    def test_del(self, fake_lib):
        ptr = 1
        fake_lib.X509_STORE_new.return_value = ptr

        # test
        store = Store()
        store.__del__()

        # validation
        fake_lib.X509_STORE_free.assert_called_with(ptr)


class TestStoreContext(TestCase):

    @patch('pulp.server.common.openssl.openssl')
    def test_construction(self, fake_lib):
        ptr = 0
        store = Mock()
        store.ptr = 2
        certificate = Mock()
        certificate.ptr = 3
        fake_lib.X509_STORE_CTX_new.return_value = ptr

        # test
        ctx = StoreContext(store, certificate)

        # validation
        fake_lib.X509_STORE_CTX_new.assert_called_with()
        fake_lib.X509_STORE_CTX_init.assert_called_with(ptr, store.ptr, certificate.ptr, None)
        self.assertEqual(ctx.ptr, ptr)

    @patch('pulp.server.common.openssl.openssl')
    def test_del(self, fake_lib):
        ptr = 1
        store = Mock()
        store.ptr = 2
        certificate = Mock()
        certificate.ptr = 3
        fake_lib.X509_STORE_CTX_new.return_value = ptr

        # test
        ctx = StoreContext(store, certificate)
        ctx.__del__()

        # validation
        fake_lib.X509_STORE_CTX_free.assert_called_with(ptr)


class TestCertificate(TestCase):

    @patch('pulp.server.common.openssl.BIO')
    @patch('pulp.server.common.openssl.openssl')
    def test_construction(self, fake_lib, fake_bio):
        ptr = 0
        fake_lib.PEM_read_bio_X509.return_value = ptr
        pem = 'PEM-ENCODED'

        # test
        certificate = Certificate(pem)

        # validation
        fake_bio.assert_called_with(pem)
        fake_lib.PEM_read_bio_X509.assert_called_with(fake_bio().ptr, None, 0, None)
        self.assertEqual(certificate.ptr, ptr)

    @patch('pulp.server.common.openssl.openssl')
    def test_del(self, fake_lib):
        ptr = 1
        fake_lib.PEM_read_bio_X509.return_value = ptr

        # test
        certificate = Certificate('')
        certificate.__del__()

        # validation
        fake_lib.X509_free.assert_called_with(ptr)

    @patch('pulp.server.common.openssl.BIO', Mock())
    @patch('pulp.server.common.openssl.Store')
    @patch('pulp.server.common.openssl.StoreContext')
    @patch('pulp.server.common.openssl.openssl')
    def test_verify(self, fake_lib, fake_ctx, fake_store):
        ptr = 0
        fake_lib.PEM_read_bio_X509.return_value = ptr
        fake_lib.X509_verify_cert.return_value = 1

        ca_chain = [Mock(), Mock(), Mock()]

        # test
        certificate = Certificate('')
        valid = certificate.verify(ca_chain)

        # validation
        calls = fake_store().add.call_args_list
        self.assertEqual(len(calls), len(ca_chain))
        for i, ca in enumerate(ca_chain):
            self.assertEqual(calls[i][0][0], ca)
        fake_ctx.assert_called_with(fake_store(), certificate)
        fake_lib.X509_verify_cert.assert_called_with(fake_ctx().ptr)
        self.assertEqual(valid, 1)
