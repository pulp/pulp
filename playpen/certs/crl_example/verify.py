#!/usr/bin/env python

import os
import sys
from optparse import OptionParser

#sys.path.insert(0, "/shared/repo/m2crypto/m2crypto/build/lib.linux-x86_64-2.7")
import M2Crypto

from pulp.repo_auth.repo_cert_utils import RepoCertUtils
from pulp.server import config

def get_parser(ca_cert, good_cert, revoked_cert, crl):
    """
    Pass in default values for ca_cert, client_cert, crl
    """
    parser = OptionParser(description="Verify a certificate against a CA with a CRL")
    parser.add_option("--ca_cert", action="store", help="CA Cert, default value %s" % (ca_cert), default=ca_cert)
    parser.add_option("--good_cert", action="store", help="Good Client Cert, default value %s" % (good_cert), default=good_cert)
    parser.add_option("--revoked_cert", action="store", help="Revoked Client Cert, default value %s" % (revoked_cert), default=revoked_cert)
    parser.add_option("--crl", action="store", help="CRL, default value %s" % (crl), default=crl)
    return parser

def get_crl_issuer(crl_path):
    # Note:
    # Scope of issuer and CRL are related
    # If CRL goes out of scope, issuer does too!
    # This means: you can not return 'issuer' from this function
    crl = M2Crypto.X509.load_crl(crl_path)
    issuer = crl.get_issuer()
    name = str(issuer)
    issuer_hash = issuer.as_hash()
    return (name, issuer_hash)

def get_cert_issuer(cert_path):
    # Note:
    # Scope of issuer and Cert are related
    # If Cert goes out of scope, issuer does too!
    cert = M2Crypto.X509.load_cert(cert_path)
    issuer = cert.get_issuer()
    name = str(issuer)
    issuer_hash = issuer.as_hash()
    return (name, issuer_hash)

def pulp_verify(ca_cert, client_cert, crl):
    repo_utils = RepoCertUtils(config.config)
    return repo_utils.validate_certificate(client_cert, ca_cert)

def create_crl_stack(crl_path):
    crl = M2Crypto.X509.load_crl(crl_path)
    crls = M2Crypto.X509.CRL_Stack()
    print "Adding crl to CRL_Stack."
    crls.push(crl)

def verify_cert_no_crl(ca_cert_path, client_cert_path):
    cacert = M2Crypto.X509.load_cert(ca_cert_path)
    cert = M2Crypto.X509.load_cert(client_cert_path)
    store = M2Crypto.X509.X509_Store()
    store.add_cert(cacert)
    store_ctx = M2Crypto.X509.X509_Store_Context()
    store_ctx.init(store, cert)
    return store_ctx.verify_cert()

def test_empty_CRL_Stack():
    crls = M2Crypto.X509.CRL_Stack()
    num = M2Crypto.X509.m2.sk_x509_crl_num(crls.stack)
    assert(num == 0)

def crl_verify(ca_cert_path, crl_path):
    cacert = M2Crypto.X509.load_cert(ca_cert_path)
    crl = M2Crypto.X509.load_crl(crl_path)
    return crl.verify(cacert.get_pubkey())

def test_load_crl_string(ca_cert_path, crl_path):
    f = open(crl_path)
    crl_data = f.read()
    f.close()
    f = open(ca_cert_path)
    ca_data = f.read()
    f.close()
    crl = M2Crypto.X509.load_crl_string(crl_data)
    ca = M2Crypto.X509.load_cert_string(ca_data)
    assert crl.verify(ca.get_pubkey())
    return (crl.get_issuer().as_hash() == ca.get_issuer().as_hash())



def verify_no_trusted_no_crl(ca_cert_path, client_cert_path):
    # Read in cacert, cert, and crl
    cacert = M2Crypto.X509.load_cert(ca_cert_path)
    cert = M2Crypto.X509.load_cert(client_cert_path)
    # Create a X509 store to hold the CA 
    store = M2Crypto.X509.X509_Store()
    store.add_cert(cacert)
    # Create a context so we can verify a certificate
    store_ctx = M2Crypto.X509.X509_Store_Context()
    store_ctx.init(store, cert)
    return store_ctx.verify_cert()

def verify_empty_trusted_with_crl(ca_cert_path, client_cert_path, crl_path):
    """
    For our purposes:
    ca_cert_path is the issuer of client_cert_path
    ca_cert_path created crl
    crl_path is revoking client_cert_path
    We want to verify the certificate and see it was revoked
    """
    # Read in cacert, cert, and crl
    cacert = M2Crypto.X509.load_cert(ca_cert_path)
    cert = M2Crypto.X509.load_cert(client_cert_path)
    crl = M2Crypto.X509.load_crl(crl_path)
    # Create a X509 store to hold the CA 
    store = M2Crypto.X509.X509_Store()
    store.add_cert(cacert)
    # Must set flags for CRL check
    store.set_flags(M2Crypto.X509.m2.X509_V_FLAG_CRL_CHECK | M2Crypto.X509.m2.X509_V_FLAG_CRL_CHECK_ALL)
    # Create a context so we can verify a certificate
    store_ctx = M2Crypto.X509.X509_Store_Context()
    untrusted = M2Crypto.X509.X509_Stack()
    store_ctx.init(store, cert, untrusted)
    crls = M2Crypto.X509.CRL_Stack()
    crls.push(crl)
    store_ctx.add_crls(crls)
    return store_ctx.verify_cert()


def verify(ca_cert_path, client_cert_path, crl_path):
    """
    For our purposes:
    ca_cert_path is the issuer of client_cert_path
    ca_cert_path created crl
    crl_path is revoking client_cert_path
    We want to verify the certificate and see it was revoked
    """
    # Read in cacert, cert, and crl
    cacert = M2Crypto.X509.load_cert(ca_cert_path)
    cert = M2Crypto.X509.load_cert(client_cert_path)
    crl = M2Crypto.X509.load_crl(crl_path)
    # Create a X509 store to hold the CA 
    store = M2Crypto.X509.X509_Store()
    store.add_cert(cacert)
    # Must set flags for CRL check
    store.set_flags(M2Crypto.X509.m2.X509_V_FLAG_CRL_CHECK | M2Crypto.X509.m2.X509_V_FLAG_CRL_CHECK_ALL)
    # Create a context so we can verify a certificate
    store_ctx = M2Crypto.X509.X509_Store_Context()
    # Remember flags, we want to set them on the 'store' before we init the context
    store_ctx.init(store, cert)
    # Add CRLs
    crls = M2Crypto.X509.CRL_Stack()
    crls.push(crl)
    store_ctx.add_crls(crls)
    return store_ctx.verify_cert()


if __name__ == "__main__":
    print "Using M2Crypto version: %s" % (M2Crypto.version)
    parser = get_parser(ca_cert="./certs/Pulp_CA.cert", good_cert="./ok/Pulp_client.cert", 
            revoked_cert="./revoked/Pulp_client.cert", crl="./certs/Pulp_CRL.pem")
    opts, args = parser.parse_args()
    ca_cert = opts.ca_cert
    revoked_cert = opts.revoked_cert
    good_cert = opts.good_cert
    crl = opts.crl

    crl_issuer_name, crl_issuer_hash = get_crl_issuer(crl)
    good_cert_issuer_name, good_cert_issuer_hash = get_cert_issuer(good_cert)
    revoked_cert_issuer_name, revoked_cert_issuer_hash = get_cert_issuer(revoked_cert)
    ca_issuer_name, ca_issuer_hash = get_cert_issuer(ca_cert)

    print "CA Issuer:           %s, Hash: %x" % (ca_issuer_name, ca_issuer_hash)
    print "CRL Issuer:          %s, Hash: %x" % (crl_issuer_name, crl_issuer_hash)
    print "Good Cert Issuer:    %s, Hash: %x" % (good_cert_issuer_name, good_cert_issuer_hash)
    print "Revoked Cert Issuer: %s, Hash: %x" % (revoked_cert_issuer_name, revoked_cert_issuer_hash)


    test_empty_CRL_Stack()
    status = crl_verify(ca_cert, crl)
    assert(status == 1)

    status = test_load_crl_string(ca_cert, crl)
    assert(status == 1)

    # Good Cert & Revoked Cert came from same CA
    # With no CRL used, both will pass
    status = verify_no_trusted_no_crl(ca_cert, good_cert)
    assert(status == 1)
    status = verify_no_trusted_no_crl(ca_cert, revoked_cert)
    assert(status == 1)

    # Now use a CRL, revoked cert should fail
    # This test will create an empty trusted chain, we want to be sure
    # M2Crypto and Openssl handle the condition of an empty untrusted chain
    status = verify_empty_trusted_with_crl(ca_cert, good_cert, crl)
    assert(status == 1)
    status = verify_empty_trusted_with_crl(ca_cert, revoked_cert, crl)
    assert(status == 0)

    status = verify(ca_cert, good_cert, crl)
    print "Testing good certificate: %s, status: %s" % (good_cert, status)
    assert(status == 1)
    status = verify(ca_cert, revoked_cert, crl)
    print "Testing revoked certificate: %s, status: %s" % (revoked_cert, status)
    assert(status == 0)
    print "Verification test passed"
