#!/usr/bin/env python

# Reference: Blog post from Jason Dobies
# http://blog.pulpproject.org/2011/05/18/pulp-protected-repositories/

import os
import shlex
import socket
import sys
import subprocess

from base import get_parser, run_command, update_openssl_config, check_dirs

def create_ca_key(ca_key_name):
    check_dirs(ca_key_name)
    cmd = "openssl genrsa -out %s 2048" % (ca_key_name)
    return run_command(cmd)

def create_ca_cert(ca_key_name, ca_cert_name, config_file):
    check_dirs(ca_key_name)
    cmd = ("openssl req -new -x509 -days 365 -key %s -out %s -config %s") % (ca_key_name, ca_cert_name, config_file)
    return run_command(cmd)

if __name__ == "__main__":
    parser = get_parser(limit_options=["ca_key", "ca_cert", "ssl_conf_ca"])
    (opts, args) = parser.parse_args()

    ca_key = opts.ca_key
    ca_cert = opts.ca_cert
    ssl_conf = opts.ssl_conf_ca

    if not create_ca_key(ca_key):
        print "Failed to create CA key"
        sys.exit(1)

    if not create_ca_cert(ca_key, ca_cert, ssl_conf):
        print "Failed to create CA cert"
        sys.exit(1)

    print "CA Key: %s" % (ca_key)
    print "CA Cert: %s" % (ca_cert)

