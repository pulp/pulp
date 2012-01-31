#!/usr/bin/env python

"""Unit tests for M2Crypto.X509.

Contributed by Toby Allsopp <toby@MI6.GEN.NZ> under M2Crypto's license.

Portions created by Open Source Applications Foundation (OSAF) are
Copyright (C) 2004-2005 OSAF. All Rights Reserved.
Author: Heikki Toivonen
"""

import unittest
import os, time, base64, sys
from M2Crypto import X509, EVP, RSA, Rand, ASN1, m2, util, BIO

class X509TestCase(unittest.TestCase):

    def callback(self, *args):
        pass

    def mkreq(self, bits, ca=0):
        pk = EVP.PKey()
        x = X509.Request()
        rsa = RSA.gen_key(bits, 65537, self.callback)
        pk.assign_rsa(rsa)
        rsa = None # should not be freed here
        x.set_pubkey(pk)
        name = x.get_subject()
        name.C = "UK"
        name.CN = "OpenSSL Group"
        if not ca:
            ext1 = X509.new_extension('subjectAltName', 'DNS:foobar.example.com')
            ext2 = X509.new_extension('nsComment', 'Hello there')
            extstack = X509.X509_Extension_Stack()
            extstack.push(ext1)
            extstack.push(ext2)
            x.add_extensions(extstack)
        self.assertRaises(ValueError, x.sign, pk, 'sha513')
        x.sign(pk,'sha1')
        assert x.verify(pk)
        pk2 = x.get_pubkey()
        assert x.verify(pk2)
        return x, pk

    def test_ext(self):
        self.assertRaises(ValueError, X509.new_extension,
                          'subjectKeyIdentifier', 'hash')
        ext = X509.new_extension('subjectAltName', 'DNS:foobar.example.com')
        assert ext.get_value() == 'DNS:foobar.example.com'
        assert ext.get_value(indent=2) == '  DNS:foobar.example.com'
        assert ext.get_value(flag=m2.X509V3_EXT_PARSE_UNKNOWN) == 'DNS:foobar.example.com'

    def test_extstack(self):
        # new
        ext1 = X509.new_extension('subjectAltName', 'DNS:foobar.example.com')
        ext2 = X509.new_extension('nsComment', 'Hello there')
        extstack = X509.X509_Extension_Stack()
        
        # push
        extstack.push(ext1)
        extstack.push(ext2)
        assert(extstack[1].get_name() == 'nsComment')
        assert len(extstack) == 2
        
        # iterator
        i = 0
        for e in extstack:
            i += 1
            assert len(e.get_name()) > 0
        assert i == 2
        
        # pop
        ext3 = extstack.pop()
        assert len(extstack) == 1
        assert(extstack[0].get_name() == 'subjectAltName')
        extstack.push(ext3)
        assert len(extstack) == 2
        assert(extstack[1].get_name() == 'nsComment')
        
        assert extstack.pop() is not None
        assert extstack.pop() is not None
        assert extstack.pop() is None

    def test_x509_name(self):
        n = X509.X509_Name()
        n.C = 'US' # It seems this actually needs to be a real 2 letter country code
        assert n.C == 'US'
        n.SP = 'State or Province'
        assert n.SP == 'State or Province'
        n.L = 'locality name'
        assert n.L == 'locality name'
        n.O = 'orhanization name'
        assert n.O == 'orhanization name'
        n.OU = 'org unit'
        assert n.OU == 'org unit'
        n.CN = 'common name'
        assert n.CN == 'common name'
        n.Email = 'bob@example.com'
        assert n.Email == 'bob@example.com'
        n.serialNumber = '1234'
        assert n.serialNumber == '1234'
        n.SN = 'surname'
        assert n.SN == 'surname'
        n.GN = 'given name'
        assert n.GN == 'given name'
        assert n.as_text() == 'C=US, ST=State or Province, L=locality name, O=orhanization name, OU=org unit, CN=common name/emailAddress=bob@example.com/serialNumber=1234, SN=surname, GN=given name', '"%s"' % n.as_text()
        assert len(n) == 10, len(n)
        n.givenName = 'name given'
        assert n.GN == 'given name' # Just gets the first
        assert n.as_text() == 'C=US, ST=State or Province, L=locality name, O=orhanization name, OU=org unit, CN=common name/emailAddress=bob@example.com/serialNumber=1234, SN=surname, GN=given name, GN=name given', '"%s"' % n.as_text()
        assert len(n) == 11, len(n)
        n.add_entry_by_txt(field="CN", type=ASN1.MBSTRING_ASC,
                           entry="Proxy", len=-1, loc=-1, set=0)
        assert len(n) == 12, len(n)
        assert n.entry_count() == 12, n.entry_count()
        assert n.as_text() == 'C=US, ST=State or Province, L=locality name, O=orhanization name, OU=org unit, CN=common name/emailAddress=bob@example.com/serialNumber=1234, SN=surname, GN=given name, GN=name given, CN=Proxy', '"%s"' % n.as_text()

        self.assertRaises(AttributeError, n.__getattr__, 'foobar')
        n.foobar = 1
        assert n.foobar == 1, n.foobar
        
        # X509_Name_Entry tests
        l = 0
        for entry in n:
            assert isinstance(entry, X509.X509_Name_Entry), entry
            assert isinstance(entry.get_object(), ASN1.ASN1_Object), entry
            assert isinstance(entry.get_data(), ASN1.ASN1_String), entry
            l += 1
        assert l == 12, l
        
        l = 0
        for cn in n.get_entries_by_nid(m2.NID_commonName):
            assert isinstance(cn, X509.X509_Name_Entry), cn
            assert isinstance(cn.get_object(), ASN1.ASN1_Object), cn
            data = cn.get_data()
            assert isinstance(data, ASN1.ASN1_String), data
            t = data.as_text()
            assert t == "common name" or t == "Proxy", t
            l += 1
        assert l == 2, l

        cn.set_data("Hello There!")
        assert cn.get_data().as_text() == "Hello There!", cn.get_data().as_text()

        assert n.as_hash() == 333998119
        
        self.assertRaises(IndexError, lambda: n[100])
        self.assert_(n[10])

    def test_mkreq(self):
        (req, _) = self.mkreq(1024)
        req.save_pem('tests/tmp_request.pem')
        req2 = X509.load_request('tests/tmp_request.pem')
        os.remove('tests/tmp_request.pem')
        req.save('tests/tmp_request.pem')
        req3 = X509.load_request('tests/tmp_request.pem')
        os.remove('tests/tmp_request.pem')
        req.save('tests/tmp_request.der', format=X509.FORMAT_DER)
        req4 = X509.load_request('tests/tmp_request.der',
                format=X509.FORMAT_DER)
        os.remove('tests/tmp_request.der')
        assert req.as_pem() == req2.as_pem()
        assert req.as_text() == req2.as_text()
        assert req.as_der() == req2.as_der()
        assert req.as_pem() == req3.as_pem()
        assert req.as_text() == req3.as_text()
        assert req.as_der() == req3.as_der()
        assert req.as_pem() == req4.as_pem()
        assert req.as_text() == req4.as_text()
        assert req.as_der() == req4.as_der()
        self.assertEqual(req.get_version(), 0)
        req.set_version(1)
        self.assertEqual(req.get_version(), 1)
        req.set_version(0)
        self.assertEqual(req.get_version(), 0)


    def test_mkcert(self):
        req, pk = self.mkreq(1024)
        pkey = req.get_pubkey()
        assert(req.verify(pkey))
        sub = req.get_subject()
        assert len(sub) == 2, len(sub)
        cert = X509.X509()
        cert.set_serial_number(1)
        cert.set_version(2)
        cert.set_subject(sub)
        t = long(time.time()) + time.timezone
        now = ASN1.ASN1_UTCTIME()
        now.set_time(t)
        nowPlusYear = ASN1.ASN1_UTCTIME()
        nowPlusYear.set_time(t + 60 * 60 * 24 * 365)
        cert.set_not_before(now)
        cert.set_not_after(nowPlusYear)
        assert str(cert.get_not_before()) == str(now)
        assert str(cert.get_not_after()) == str(nowPlusYear)
        issuer = X509.X509_Name()
        issuer.CN = 'The Issuer Monkey'
        issuer.O = 'The Organization Otherwise Known as My CA, Inc.'
        cert.set_issuer(issuer)
        cert.set_pubkey(pkey)
        cert.set_pubkey(cert.get_pubkey()) # Make sure get/set work
        ext = X509.new_extension('subjectAltName', 'DNS:foobar.example.com')
        ext.set_critical(0)
        assert ext.get_critical() == 0
        cert.add_ext(ext)
        cert.sign(pk, 'sha1')
        self.assertRaises(ValueError, cert.sign, pk, 'nosuchalgo')
        assert(cert.get_ext('subjectAltName').get_name() == 'subjectAltName')
        assert(cert.get_ext_at(0).get_name() == 'subjectAltName')
        assert(cert.get_ext_at(0).get_value() == 'DNS:foobar.example.com')
        assert cert.get_ext_count() == 1, cert.get_ext_count()
        self.assertRaises(IndexError, cert.get_ext_at, 1)
        assert cert.verify()
        assert cert.verify(pkey)
        assert cert.verify(cert.get_pubkey())
        assert cert.get_version() == 2
        assert cert.get_serial_number() == 1
        assert cert.get_issuer().CN == 'The Issuer Monkey' 
        
        if m2.OPENSSL_VERSION_NUMBER >= 0x90800f:
            assert not cert.check_ca()
            assert not cert.check_purpose(m2.X509_PURPOSE_SSL_SERVER, 1)
            assert not cert.check_purpose(m2.X509_PURPOSE_NS_SSL_SERVER, 1)
            assert cert.check_purpose(m2.X509_PURPOSE_SSL_SERVER, 0)
            assert cert.check_purpose(m2.X509_PURPOSE_NS_SSL_SERVER, 0)
            assert cert.check_purpose(m2.X509_PURPOSE_ANY, 0)            
        else:
            self.assertRaises(AttributeError, cert.check_ca)

    def mkcacert(self):
        req, pk = self.mkreq(1024, ca=1)
        pkey = req.get_pubkey()
        sub = req.get_subject()
        cert = X509.X509()
        cert.set_serial_number(1)
        cert.set_version(2)
        cert.set_subject(sub)
        t = long(time.time()) + time.timezone
        now = ASN1.ASN1_UTCTIME()
        now.set_time(t)
        nowPlusYear = ASN1.ASN1_UTCTIME()
        nowPlusYear.set_time(t + 60 * 60 * 24 * 365)
        cert.set_not_before(now)
        cert.set_not_after(nowPlusYear)
        issuer = X509.X509_Name()
        issuer.C = "UK"
        issuer.CN = "OpenSSL Group"
        cert.set_issuer(issuer)
        cert.set_pubkey(pkey) 
        ext = X509.new_extension('basicConstraints', 'CA:TRUE')
        cert.add_ext(ext)
        cert.sign(pk, 'sha1')

        if m2.OPENSSL_VERSION_NUMBER >= 0x0090800fL:
            assert cert.check_ca()
            assert cert.check_purpose(m2.X509_PURPOSE_SSL_SERVER, 1)
            assert cert.check_purpose(m2.X509_PURPOSE_NS_SSL_SERVER, 1)
            assert cert.check_purpose(m2.X509_PURPOSE_ANY, 1)
            assert cert.check_purpose(m2.X509_PURPOSE_SSL_SERVER, 0)
            assert cert.check_purpose(m2.X509_PURPOSE_NS_SSL_SERVER, 0)
            assert cert.check_purpose(m2.X509_PURPOSE_ANY, 0)
        else:
            self.assertRaises(AttributeError, cert.check_ca)
        
        return cert, pk, pkey

    def test_mkcacert(self): 
        cacert, pk, pkey = self.mkcacert()
        assert cacert.verify(pkey)
        

    def test_mkproxycert(self): 
        cacert, pk1, pkey = self.mkcacert()
        end_entity_cert_req, pk2 = self.mkreq(1024)
        end_entity_cert = self.make_eecert(cacert)
        end_entity_cert.set_subject(end_entity_cert_req.get_subject())
        end_entity_cert.set_pubkey(end_entity_cert_req.get_pubkey())
        end_entity_cert.sign(pk1, 'sha1')
        proxycert = self.make_proxycert(end_entity_cert)
        proxycert.sign(pk2, 'sha1')
        assert proxycert.verify(pk2)
        assert proxycert.get_ext_at(0).get_name() == 'proxyCertInfo', proxycert.get_ext_at(0).get_name()
        assert proxycert.get_ext_at(0).get_value() == 'Path Length Constraint: infinite\nPolicy Language: Inherit all\n', '"%s"' % proxycert.get_ext_at(0).get_value()
        assert proxycert.get_ext_count() == 1, proxycert.get_ext_count()
        assert proxycert.get_subject().as_text() == 'C=UK, CN=OpenSSL Group, CN=Proxy', proxycert.get_subject().as_text()
        assert proxycert.get_subject().as_text(indent=2, flags=m2.XN_FLAG_RFC2253) == '  CN=Proxy,CN=OpenSSL Group,C=UK', '"%s"' %  proxycert.get_subject().as_text(indent=2, flags=m2.XN_FLAG_RFC2253)

    def make_eecert(self, cacert):
        eecert = X509.X509()
        eecert.set_serial_number(2)
        eecert.set_version(2)
        t = long(time.time()) + time.timezone
        now = ASN1.ASN1_UTCTIME()
        now.set_time(t)
        now_plus_year = ASN1.ASN1_UTCTIME()
        now_plus_year.set_time(t + 60 * 60 * 24 * 365)
        eecert.set_not_before(now)
        eecert.set_not_after(now_plus_year)
        eecert.set_issuer(cacert.get_subject())
        return eecert
    
    def make_proxycert(self, eecert):
        proxycert = X509.X509()
        pk2 = EVP.PKey()
        proxykey =  RSA.gen_key(1024, 65537, self.callback)
        pk2.assign_rsa(proxykey)
        proxycert.set_pubkey(pk2)
        proxycert.set_version(2)
        not_before = ASN1.ASN1_UTCTIME()
        not_after = ASN1.ASN1_UTCTIME()
        not_before.set_time(int(time.time()))
        offset = 12 * 3600
        not_after.set_time(int(time.time()) + offset )
        proxycert.set_not_before(not_before)
        proxycert.set_not_after(not_after)
        proxycert.set_issuer_name(eecert.get_subject())
        proxycert.set_serial_number(12345678)
        proxy_subject_name = X509.X509_Name()
        issuer_name_string = eecert.get_subject().as_text()
        seq = issuer_name_string.split(",")

        subject_name = X509.X509_Name()
        for entry in seq:
            l = entry.split("=")
            subject_name.add_entry_by_txt(field=l[0].strip(),
                                          type=ASN1.MBSTRING_ASC,
                                          entry=l[1], len=-1, loc=-1, set=0)

        subject_name.add_entry_by_txt(field="CN", type=ASN1.MBSTRING_ASC,
                                      entry="Proxy", len=-1, loc=-1, set=0)


        proxycert.set_subject_name(subject_name)
        pci_ext = X509.new_extension("proxyCertInfo", 
                                     "critical,language:Inherit all", 1) # XXX leaks 8 bytes 
        proxycert.add_ext(pci_ext)
        return proxycert
    
    def test_fingerprint(self):
        x509 = X509.load_cert('tests/x509.pem')
        fp = x509.get_fingerprint('sha1')
        expected = '8D2EB9E203B5FFDC7F4FA7DC4103E852A55B808D'
        assert fp == expected, '%s != %s' % (fp, expected)

    def test_load_der_string(self):
        f = open('tests/x509.der', 'rb')
        x509 = X509.load_cert_der_string(''.join(f.readlines()))
        fp = x509.get_fingerprint('sha1')
        expected = '8D2EB9E203B5FFDC7F4FA7DC4103E852A55B808D'
        assert fp == expected, '%s != %s' % (fp, expected)

    def test_save_der_string(self):
        x509 = X509.load_cert('tests/x509.pem')
        s = x509.as_der()
        f = open('tests/x509.der', 'rb')
        s2 = f.read()
        f.close()
        assert s == s2

    def test_load(self):
        x509 = X509.load_cert('tests/x509.pem')
        x5092 = X509.load_cert('tests/x509.der', format=X509.FORMAT_DER)
        assert x509.as_text() == x5092.as_text()
        assert x509.as_pem() == x5092.as_pem()
        assert x509.as_der() == x5092.as_der()
        return
    
    def test_load_bio(self):
        bio = BIO.openfile('tests/x509.pem')
        bio2 = BIO.openfile('tests/x509.der')
        x509 = X509.load_cert_bio(bio)
        x5092 = X509.load_cert_bio(bio2, format=X509.FORMAT_DER)
        
        self.assertRaises(ValueError, X509.load_cert_bio, bio2, format=45678)

        assert x509.as_text() == x5092.as_text()
        assert x509.as_pem() == x5092.as_pem()
        assert x509.as_der() == x5092.as_der()
        return

    def test_load_string(self):
        f = open('tests/x509.pem')
        s = f.read()
        f.close()
        f2 = open('tests/x509.der', 'rb')
        s2 = f2.read()
        f2.close()
        x509 = X509.load_cert_string(s)
        x5092 = X509.load_cert_string(s2, X509.FORMAT_DER)
        assert x509.as_text() == x5092.as_text()
        assert x509.as_pem() == x5092.as_pem()
        assert x509.as_der() == x5092.as_der()
        return
    
    def test_load_request_bio(self):
        (req, _) = self.mkreq(512)

        r1 = X509.load_request_der_string(req.as_der())
        r2 = X509.load_request_string(req.as_der(), X509.FORMAT_DER)
        r3 = X509.load_request_string(req.as_pem(), X509.FORMAT_PEM)

        r4 = X509.load_request_bio(BIO.MemoryBuffer(req.as_der()), X509.FORMAT_DER)
        r5 = X509.load_request_bio(BIO.MemoryBuffer(req.as_pem()), X509.FORMAT_PEM)

        for r in [r1, r2, r3, r4, r5]:
            assert req.as_der() == r.as_der()

        self.assertRaises(ValueError, X509.load_request_bio, BIO.MemoryBuffer(req.as_pem()), 345678)

    def test_save(self):
        x509 = X509.load_cert('tests/x509.pem')
        f = open('tests/x509.pem', 'r')
        lTmp = f.readlines()
        x509_pem = ''.join(lTmp[44:60]) # -----BEGIN CERTIFICATE----- : -----END CERTIFICATE-----
        f.close()
        f = open('tests/x509.der', 'rb')
        x509_der = f.read()
        f.close()
        x509.save('tests/tmpcert.pem')
        f = open('tests/tmpcert.pem')
        s = f.read()
        f.close()
        self.assertEquals(s, x509_pem)
        os.remove('tests/tmpcert.pem')
        x509.save('tests/tmpcert.der', format=X509.FORMAT_DER)
        f = open('tests/tmpcert.der', 'rb')
        s = f.read()
        f.close()
        self.assertEquals(s, x509_der)
        os.remove('tests/tmpcert.der')

    def test_malformed_data(self):
        self.assertRaises(X509.X509Error, X509.load_cert_string, 'Hello')
        self.assertRaises(X509.X509Error, X509.load_cert_der_string, 'Hello')
        self.assertRaises(X509.X509Error, X509.new_stack_from_der, 'Hello')
        self.assertRaises(X509.X509Error, X509.load_cert, 'tests/alltests.py')
        self.assertRaises(X509.X509Error, X509.load_request, 'tests/alltests.py')
        self.assertRaises(X509.X509Error, X509.load_request_string, 'Hello')
        self.assertRaises(X509.X509Error, X509.load_request_der_string, 'Hello')
        self.assertRaises(X509.X509Error, X509.load_crl, 'tests/alltests.py')
        
    def test_long_serial(self):
        from M2Crypto import X509
        cert = X509.load_cert('tests/long_serial_cert.pem')
        self.assertEquals(cert.get_serial_number(), 17616841808974579194)

        cert = X509.load_cert('tests/thawte.pem')
        self.assertEquals(cert.get_serial_number(), 127614157056681299805556476275995414779)


class X509_StackTestCase(unittest.TestCase):
    
    def test_make_stack_from_der(self):
        f = open("tests/der_encoded_seq.b64")
        b64 = f.read(1304)
        seq = base64.decodestring(b64)
        stack = X509.new_stack_from_der(seq)
        cert = stack.pop()
        assert stack.pop() is None
        
        cert.foobar = 1
        assert cert.foobar == 1
        
        subject = cert.get_subject() 
        assert str(subject) == "/DC=org/DC=doegrids/OU=Services/CN=host/bosshog.lbl.gov"

    def test_make_stack_check_num(self):
        f = open("tests/der_encoded_seq.b64")
        b64 = f.read(1304)
        seq = base64.decodestring(b64)
        stack = X509.new_stack_from_der(seq)
        num = len(stack)
        assert num == 1 
        cert = stack.pop() 
        num = len(stack)
        assert num == 0 
        subject = cert.get_subject() 
        assert str(subject) == "/DC=org/DC=doegrids/OU=Services/CN=host/bosshog.lbl.gov"

    def test_make_stack(self):
        stack = X509.X509_Stack()
        cert = X509.load_cert("tests/x509.pem")
        issuer = X509.load_cert("tests/ca.pem")
        cert_subject1 = cert.get_subject()
        issuer_subject1 = issuer.get_subject()
        stack.push(cert)
        stack.push(issuer)
        
        # Test stack iterator
        i = 0
        for c in stack:
            i += 1
            assert len(c.get_subject().CN) > 0
        assert i == 2
        
        issuer_pop = stack.pop() 
        cert_pop = stack.pop() 
        cert_subject2 = cert_pop.get_subject() 
        issuer_subject2 = issuer.get_subject()
        assert str(cert_subject1) == str(cert_subject2)
        assert str(issuer_subject1) == str(issuer_subject2)
    
    def test_as_der(self):
        stack = X509.X509_Stack()
        cert = X509.load_cert("tests/x509.pem")
        issuer = X509.load_cert("tests/ca.pem")
        cert_subject1 = cert.get_subject()
        issuer_subject1 = issuer.get_subject()
        stack.push(cert)
        stack.push(issuer)
        der_seq = stack.as_der() 
        stack2 = X509.new_stack_from_der(der_seq)
        issuer_pop = stack2.pop() 
        cert_pop = stack2.pop() 
        cert_subject2 = cert_pop.get_subject() 
        issuer_subject2 = issuer.get_subject()
        assert str(cert_subject1) == str(cert_subject2)
        assert str(issuer_subject1) == str(issuer_subject2)
        

class X509_ExtTestCase(unittest.TestCase):
    
    def test_ext(self):
        if 0: # XXX
            # With this leaks 8 bytes:
            name = "proxyCertInfo"
            value = "critical,language:Inherit all"
        else:
            # With this there are no leaks:
            name = "nsComment"
            value = "Hello"
        
        lhash = m2.x509v3_lhash()
        ctx = m2.x509v3_set_conf_lhash(lhash)
        x509_ext_ptr = m2.x509v3_ext_conf(lhash, ctx, name, value)
        x509_ext = X509.X509_Extension(x509_ext_ptr, 1)

class X509_StoreContextTestCase(unittest.TestCase):

    def test_verify_cert(self):
        # Test with the CA that signed tests/x509.pem
        ca = X509.load_cert('tests/ca.pem')
        cert = X509.load_cert('tests/x509.pem')
        store = X509.X509_Store()
        store.add_x509(ca)
        store_ctx = X509.X509_Store_Context()
        store_ctx.init(store, cert)
        self.assertTrue(store_ctx.verify_cert())

        # Test with the wrong CA, this CA did not sign tests/x509.pem
        wrong_ca = X509.load_cert("tests/crl_data/certs/revoking_ca.pem")
        cert = X509.load_cert('tests/x509.pem')
        store = X509.X509_Store()
        store.add_x509(wrong_ca)
        store_ctx = X509.X509_Store_Context()
        store_ctx.init(store, cert)
        self.assertFalse(store_ctx.verify_cert())

    def test_verify_with_add_crl(self):
        ca = X509.load_cert("tests/crl_data/certs/revoking_ca.pem")
        valid_cert = X509.load_cert('tests/crl_data/certs/valid_cert.pem')
        revoked_cert = X509.load_cert('tests/crl_data/certs/revoked_cert.pem')
        crl = X509.load_crl('tests/crl_data/certs/revoking_crl.pem')

        # Verify that a good cert is verified OK
        store = X509.X509_Store()
        store.add_x509(ca)
        store.add_crl(crl)
        store.set_flags(X509.m2.X509_V_FLAG_CRL_CHECK |
                       X509.m2.X509_V_FLAG_CRL_CHECK_ALL)
        store_ctx = X509.X509_Store_Context()
        store_ctx.init(store, valid_cert)
        self.assertTrue(store_ctx.verify_cert())

        # Verify that a revoked cert is not verified
        store = X509.X509_Store()
        store.add_x509(ca)
        store.add_crl(crl)
        store.set_flags(X509.m2.X509_V_FLAG_CRL_CHECK |
                       X509.m2.X509_V_FLAG_CRL_CHECK_ALL)
        store_ctx = X509.X509_Store_Context()
        store_ctx.init(store, revoked_cert)
        self.assertFalse(store_ctx.verify_cert())

    def test_verify_with_add_crls(self):
        ca = X509.load_cert("tests/crl_data/certs/revoking_ca.pem")
        valid_cert = X509.load_cert('tests/crl_data/certs/valid_cert.pem')
        revoked_cert = X509.load_cert('tests/crl_data/certs/revoked_cert.pem')
        crl = X509.load_crl('tests/crl_data/certs/revoking_crl.pem')

        # Verify that a good cert is verified OK
        store = X509.X509_Store()
        store.add_x509(ca)
        store.set_flags(X509.m2.X509_V_FLAG_CRL_CHECK |
                       X509.m2.X509_V_FLAG_CRL_CHECK_ALL)
        crl_stack = X509.CRL_Stack()
        crl_stack.push(crl)
        store_ctx = X509.X509_Store_Context()
        store_ctx.init(store, valid_cert)
        store_ctx.add_crls(crl_stack)
        self.assertTrue(store_ctx.verify_cert())

        # Verify that a revoked cert is not verified
        store = X509.X509_Store()
        store.add_x509(ca)
        store.set_flags(X509.m2.X509_V_FLAG_CRL_CHECK |
                       X509.m2.X509_V_FLAG_CRL_CHECK_ALL)
        crl_stack = X509.CRL_Stack()
        crl_stack.push(crl)
        store_ctx = X509.X509_Store_Context()
        store_ctx.init(store, revoked_cert)
        store_ctx.add_crls(crl_stack)
        self.assertFalse(store_ctx.verify_cert())

class CRL_StackTestCase(unittest.TestCase):
    def test_new(self):
        crl_stack = X509.CRL_Stack()
        self.assertIsNotNone(crl_stack)
        self.assertEqual(len(crl_stack), 0)

    def test_push_and_pop(self):
        crl_stack = X509.CRL_Stack()
        crl_a = X509.CRL()
        crl_b = X509.CRL()
        self.assertNotEqual(crl_a, crl_b)
        crl_stack.push(crl_a)
        crl_stack.push(crl_b)
        self.assertEquals(len(crl_stack), 2)
        popped_b = crl_stack.pop()
        self.assertEquals(crl_b, popped_b)
        self.assertEquals(len(crl_stack), 1)
        popped_a = crl_stack.pop()
        self.assertEqual(crl_a, popped_a)
        self.assertEqual(len(crl_stack), 0)

class CRLTestCase(unittest.TestCase):
    def test_new(self):
        crl = X509.CRL()
        self.assertEqual(crl.as_text()[:34],
                         'Certificate Revocation List (CRL):')

    def test_verify(self):
        ca = X509.load_cert("tests/crl_data/certs/revoking_ca.pem")
        crl = X509.load_crl('tests/crl_data/certs/revoking_crl.pem')
        self.assertTrue(crl.verify(ca.get_pubkey()))

        wrong_ca = X509.load_cert('tests/ca.pem')
        self.assertFalse(crl.verify(wrong_ca.get_pubkey()))

    def test_get_issuer(self):
        ca = X509.load_cert("tests/crl_data/certs/revoking_ca.pem")
        crl = X509.load_crl('tests/crl_data/certs/revoking_crl.pem')
        ca_issuer = ca.get_issuer()
        crl_issuer = crl.get_issuer()
        self.assertEqual(ca_issuer.as_hash(), crl_issuer.as_hash())

        wrong_ca = X509.load_cert('tests/ca.pem')
        wrong_ca_issuer = wrong_ca.get_issuer()
        self.assertNotEqual(wrong_ca_issuer.as_hash(), crl_issuer.as_hash())

    def test_load_crl(self):
        crl = X509.load_crl('tests/crl_data/certs/revoking_crl.pem')
        self.assertIsNotNone(crl)
        self.assertIsInstance(crl, X509.CRL)

    def test_load_crl_string(self):
        f = open('tests/crl_data/certs/revoking_crl.pem')
        data = f.read()
        f.close()
        crl = X509.load_crl_string(data)
        self.assertIsInstance(crl, X509.CRL)

        ca = X509.load_cert("tests/crl_data/certs/revoking_ca.pem")
        ca_issuer = ca.get_issuer()
        crl_issuer = crl.get_issuer()
        self.assertEqual(ca_issuer.as_hash(), crl_issuer.as_hash())

    def test_get_last_updated(self):
        expected_lastUpdate = "Jan 19 16:55:58 2012 GMT"
        crl = X509.load_crl('tests/crl_data/certs/revoking_crl.pem')
        self.assertEquals(str(crl.get_lastUpdate()), expected_lastUpdate)

    def test_get_next_update(self):
        expected_nextUpdate = "Jan 18 16:55:58 2015 GMT"
        crl = X509.load_crl('tests/crl_data/certs/revoking_crl.pem')
        self.assertEquals(str(crl.get_nextUpdate()), expected_nextUpdate)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(X509TestCase))
    suite.addTest(unittest.makeSuite(X509_StackTestCase))
    suite.addTest(unittest.makeSuite(X509_ExtTestCase))
    suite.addTest(unittest.makeSuite(X509_StoreContextTestCase))
    suite.addTest(unittest.makeSuite(CRLTestCase))
    suite.addTest(unittest.makeSuite(CRL_StackTestCase))
    return suite


if __name__ == '__main__':
    Rand.load_file('randpool.dat', -1)
    unittest.TextTestRunner().run(suite())
    Rand.save_file('randpool.dat')
