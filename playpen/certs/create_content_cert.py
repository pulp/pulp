#!/usr/bin/env python

# Reference: Blog post from Jason Dobies
# http://blog.pulpproject.org/2011/05/18/pulp-protected-repositories/

import os
import sys

from base import run_command, get_parser, update_openssl_config

def create_ent_key(ent_key):
    cmd = "openssl genrsa -out %s 2048" % (ent_key)
    return run_command(cmd)

def create_ent_csr(ent_key, csr_config, csr):
    cmd = "openssl req -new -key %s -out %s -config %s" % (ent_key, csr, csr_config)
    return run_command(cmd)

def create_ent_cert(ent_cert, ent_csr, ca_cert, ca_key, extensions, ent_name, ca_serial):
    cmd = "openssl x509 -req -days 365 -CA %s -CAkey %s -extfile %s -extensions %s -in %s -out %s -CAserial %s" \
            % (ca_cert, ca_key, extensions, ent_name, ent_csr, ent_cert, ca_serial)
    if not os.path.exists(ca_serial):
        cmd = cmd + " -CAcreateserial"
    return run_command(cmd)

if __name__ == "__main__":
    parser = get_parser()
    (opts, args) = parser.parse_args()

    ssl_conf_template = opts.ssl_conf_template
    ssl_conf = opts.ssl_conf
    hostname = opts.hostname
    ent_key = opts.ent_key
    ent_cert = opts.ent_cert
    ent_csr = opts.ent_csr
    ca_key = opts.ca_key
    ca_cert = opts.ca_cert
    ent_name = opts.ent
    extensions = opts.ext
    ca_serial = opts.ca_serial

    if not update_openssl_config(ssl_conf_template, ssl_conf, hostname):
        print "Failed to create cert configuration file"
        sys.exit(1)

    if not create_ent_key(ent_key):
        print "Failed to create entitlement key"
        sys.exit(1)

    if not create_ent_csr(ent_key, ssl_conf, ent_csr):
        print "Failed to create entitlement csr"
        sys.exit(1)

    if not create_ent_cert(ent_cert, ent_csr, ca_cert, 
            ca_key, extensions, ent_name, ca_serial):
        print "Failed to create entitlement cert"
        sys.exit(1)

    print "Entitlement Cert: %s" % (ent_cert)
    print "Entitlement Key: %s" % (ent_key)
