#!/usr/bin/env python

import os
import sys

from base import run_command, get_parser, update_openssl_config


def setup_env(index_path, crlnumber_path):
    if not os.path.exists(os.path.dirname(index_path)):
        os.makedirs(os.path.dirname(index_path))
    if not os.path.exists(os.path.dirname(crlnumber_path)):
        os.makedirs(os.path.dirname(crlnumber_path))
    if not os.path.exists(index_path):
        f = open(index_path, "w")
        f.close()
    if not os.path.exists(crlnumber_path):
        #echo "01" > ./certs/crlnumber
        f = open(crlnumber_path, "w")
        f.write("01")
        f.close()
    return True

def revoke_cert(crl_path, cert_to_revoke, ca_cert, ca_key, ssl_conf):
    # openssl ca -revoke bad_crt_file -keyfile ca_key -cert ca_crt
    # rhel5 needs -md sha1, it complains about the 'default_md' option in openssl config
    cmd = "openssl ca -revoke %s -keyfile %s -cert %s -config %s -md sha1" % (cert_to_revoke, ca_key, ca_cert, ssl_conf)
    if not run_command(cmd):
        return False
    # openssl ca -gencrl -config openssl.cnf -keyfile ./Pulp_CA.key -cert Pulp_CA.cert -out my_crl.pem
    cmd = "openssl ca -gencrl -keyfile %s -cert %s -out %s -config %s -crlexts crl_ext -md sha1" % (ca_key, ca_cert, crl_path, ssl_conf)
    if not run_command(cmd):
        return False
    return True

if __name__ == "__main__":
    parser = get_parser(limit_options=["index", "crlnumber", "ssl_conf_template_crl", "ssl_conf_crl", "ca_key", "ca_cert", "crl"])
    (opts, args) = parser.parse_args()

    index = opts.index
    crlnumber = opts.crlnumber
    ssl_conf_template_crl = opts.ssl_conf_template_crl
    ssl_conf_crl = opts.ssl_conf_crl
    ca_key = opts.ca_key
    ca_cert = opts.ca_cert
    crl = opts.crl
    
    if len(args) < 1:
        print "No certificate to revoke was given"
        print "Please re-run with certificate to revoke as command line argument"
        sys.exit(1)

    cert_to_revoke = args[0]

    if not update_openssl_config(ssl_conf_template_crl, ssl_conf_crl, index=index, crlnumber=crlnumber):
        print "Failed to create cert configuration file"
        sys.exit(1)

    if not setup_env(index, crlnumber):
        print "Failed to setup environment for CRL"
        sys.exit(1)

    if not revoke_cert(crl, cert_to_revoke, ca_cert, ca_key, ssl_conf_crl):
        print "Failed to revoke cert"
        sys.exit(1)

    print "Revoked cert: %s" % (cert_to_revoke)
    print "CRL generated at: %s" % (crl)
