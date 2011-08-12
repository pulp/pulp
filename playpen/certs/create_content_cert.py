#!/usr/bin/env python

# Reference: Blog post from Jason Dobies
# http://blog.pulpproject.org/2011/05/18/pulp-protected-repositories/

from optparse import OptionParser
import os
import shlex
import socket
import sys
import subprocess

from create_ca import run_command, write_template

CSR_TEMPLATE = """
 [ req ]
 default_bits           = 2048
 distinguished_name     = req_distinguished_name
 prompt                 = no
 [ req_distinguished_name ]
 C                      = US
 ST                     = NC
 L                      = Raleigh
 O                      = Red Hat
 OU                     = Pulp 
 CN                     = REPLACE_COMMON_NAME
 emailAddress           = pulp@example.com
"""

def create_ent_key(ent_key):
    if not os.path.exists(ent_key):
        cmd = "openssl genrsa -out %s 2048" % (ent_key)
        if not run_command(cmd):
            return False
    return True

def create_ent_csr(ent_key, csr_config, csr):
    if not os.path.exists(csr):
        cmd = "openssl req -new -key %s -out %s -config %s" % (ent_key, csr, csr_config)
        if not run_command(cmd):
            return False
    return True

def create_ent_cert(ent_cert, ent_csr, ca_cert, ca_key, extensions, ent_name):
    if not os.path.exists(ent_cert):
        cmd = "openssl x509 -req -days 365 -CA %s -CAkey %s -CAcreateserial -extfile %s -extensions %s -in %s -out %s" % (ca_cert, ca_key, extensions, ent_name, ent_csr, ent_cert)
        if not run_command(cmd):
            return False
    return True

def parse_args():
    parser = OptionParser(description=
        "Helper utility to create certs for repository authentication")
    parser.add_option('--dir', action='store',
                help='Cert Directory', default='certs')
    parser.add_option('--ext', action='store', 
                help='Extensions file', default="extensions.txt")
    parser.add_option('--ent', action='store', 
                help='Entitlement name, default is "pulp-repos"', 
                default="pulp-repos")
    parser.add_option('--csr', action='store', 
                help='CSR Path', default="ent.csr")
    parser.add_option('--ent_key', action='store', 
                help='Entitlement Key Path', default="ent.key")
    parser.add_option('--ent_cert', action='store', 
                help='Entitlement Cert Path', default="ent.cert")
    parser.add_option('--ent_csr', action='store', 
                help='Entitlement CSR', default="ent.csr")
    parser.add_option('--csr_config', action='store', 
                help='CSR Configuration File', default="ent_csr.cfg")
    parser.add_option('--ca_key', action='store', 
                help='CA key filename', default="Pulp_CA.key")
    parser.add_option('--ca_cert', action='store', 
                help='CA cert filename', default="Pulp_CA.crt")
    parser.add_option('--hostname', action='store',
                help='Hostname for Certs', default=None)
    (opts, args) = parser.parse_args()
    return opts, args

if __name__ == "__main__":
    (opts, args) = parse_args()
    
    if not os.path.exists(opts.dir):
        os.makedirs(opts.dir)
    csr = os.path.join(opts.dir, opts.csr)
    csr_config = os.path.join(opts.dir, opts.csr_config)
    ent_key = os.path.join(opts.dir, opts.ent_key)
    ent_cert = os.path.join(opts.dir, opts.ent_cert)
    ent_csr = os.path.join(opts.dir, opts.ent_csr)
    ca_key = os.path.join(opts.dir, opts.ca_key)
    ca_cert = os.path.join(opts.dir, opts.ca_cert)
    ent_name = opts.ent
    
    #Input File
    extensions = opts.ext

    if not os.path.exists(csr_config):
        if not write_template(output_name=csr_config, 
                template=CSR_TEMPLATE, hostname=opts.hostname):
            print "Failed to create entitlement csr configuration file"
            sys.exit(1)
    if not create_ent_key(ent_key):
        print "Failed to create entitlement key"
        sys.exit(1)
    if not create_ent_csr(ent_key, csr_config, csr):
        print "Failed to create entitlement csr"
        sys.exit(1)
    if not create_ent_cert(ent_cert, ent_csr, ca_cert, 
            ca_key, extensions, ent_name):
        print "Failed to create entitlement cert"
        sys.exit(1)

    print "Entitlement Cert: %s" % (ent_cert)
    print "Entitlement Key: %s" % (ent_key)
