#!/usr/bin/env python

import os
import sys
from optparse import OptionParser

sys.path.insert(0, "/shared/repo/m2crypto/m2crypto/build/lib.linux-x86_64-2.7")
import M2Crypto

from pulp.repo_auth.repo_cert_utils import RepoCertUtils
from pulp.server import config

def get_parser(ca_cert, client_cert, crl):
    """
    Pass in default values for ca_cert, client_cert, crl
    """
    parser = OptionParser(description="Verify a certificate against a CA with a CRL")
    parser.add_option("--ca_cert", action="store", help="CA Cert, default value %s" % (ca_cert), default=ca_cert)
    parser.add_option("--client_cert", action="store", help="Client Cert, default value %s" % (client_cert), default=client_cert)
    parser.add_option("--crl", action="store", help="CRL, default value %s" % (crl), default=crl)
    return parser

def verify(ca_cert_path, client_cert_path, crl_path):
    """
    For our purposes:
    cacert is the issuer of cert
    cacert created crl
    crl is revoking cert
    We want to verify the certificate and see it was revoked
    """
    # Read in cacert, cert, and crl
    cacert = M2Crypto.X509.load_cert(ca_cert_path)
    cert = M2Crypto.X509.load_cert(client_cert_path)
    crl = M2Crypto.X509.load_crl(crl_path)
    # Create a X509 store to hold the CA 
    # TODO: Later explore what happens if we add a CRL to the store and not the context
    store = M2Crypto.X509.X509_Store()
    store.add_cert(cacert)
    store.add_crl(crl)
    # Must set flags for CRL check
    store.set_flags(M2Crypto.X509.m2.X509_V_FLAG_CRL_CHECK | M2Crypto.X509.m2.X509_V_FLAG_CRL_CHECK_ALL)
    # Create a context so we can verify a certificate
    store_ctx = M2Crypto.X509.X509_Store_Context()
    untrusted = M2Crypto.X509.X509_Stack()
    #untrusted.push(cert)
    store_ctx.init(store, cert, untrusted=untrusted)
    crls = M2Crypto.X509.CRL_Stack()
    #crls.push(crl)
    #print "sk_x509_crl_num(%s) = %s" % (crls.stack, M2Crypto.X509.m2.sk_x509_crl_num(crls.stack))
    store_ctx.add_crls(crls)
    ret = store_ctx.verify_cert()
    print "Verify of cert through store context: %s" % (ret)
    return True


if __name__ == "__main__":
    print "Using M2Crypto version: %s" % (M2Crypto.version)
    parser = get_parser(ca_cert="./certs/Pulp_CA.cert", client_cert="./revoked/Pulp_client.cert", crl="./certs/Pulp_CRL.pem")
    opts, args = parser.parse_args()
    ca_cert = opts.ca_cert
    client_cert = opts.client_cert
    crl = opts.crl
    print "Calling verification with CRL info"
    if verify(ca_cert, client_cert, crl):
        print "OK:  %s is a valid cert from CA: %s" % (client_cert, ca_cert)
    else:
        print "A"
        print "ERROR: %s is not a valid cert from CA: %s" % (client_cert, ca_cert)
