#!/usr/bin/env python

# Reference: Blog post from Jason Dobies
# http://blog.pulpproject.org/2011/05/18/pulp-protected-repositories/

import os
import sys

from base import run_command, get_parser

def create_client_key(client_key):
    cmd = "openssl genrsa -out %s 2048" % (client_key)
    return run_command(cmd)

def create_client_csr(client_key, csr):
    cmd = "openssl req -new -key %s -out %s -subj '/C=US/ST=NC/L=Raleigh/O=Red Hat/OU=Pulp/CN=Pulp_Content_Cert'" % (client_key, csr)
    return run_command(cmd)

def create_client_cert(client_cert, client_csr, ca_cert, ca_key, extensions, ent_name, ca_serial):
    cmd = "openssl x509 -req -days 10950 -CA %s -CAkey %s -extfile %s -extensions %s -in %s -out %s -CAserial %s" \
            % (ca_cert, ca_key, extensions, ent_name, client_csr, client_cert, ca_serial)
    if not os.path.exists(ca_serial):
        cmd = cmd + " -CAcreateserial"
    return run_command(cmd)

if __name__ == "__main__":
    parser = get_parser(limit_options=["client_key", "client_csr", "client_cert",
            "ca_key", "ca_cert", "ent", "ext", "ca_serial"])
    (opts, args) = parser.parse_args()

    client_key = opts.client_key
    client_cert = opts.client_cert
    client_csr = opts.client_csr
    ca_key = opts.ca_key
    ca_cert = opts.ca_cert
    ent_name = opts.ent
    extensions = opts.ext
    ca_serial = opts.ca_serial

    if not create_client_key(client_key):
        print "Failed to create client key"
        sys.exit(1)

    if not create_client_csr(client_key, client_csr):
        print "Failed to create client csr"
        sys.exit(1)

    if not create_client_cert(client_cert, client_csr, ca_cert, 
            ca_key, extensions, ent_name, ca_serial):
        print "Failed to create client cert"
        sys.exit(1)

    print "Client Cert: %s" % (client_cert)
    print "Client Key: %s" % (client_key)
