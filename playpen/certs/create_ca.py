#!/usr/bin/env python

# Reference: Blog post from Jason Dobies
# http://blog.pulpproject.org/2011/05/18/pulp-protected-repositories/

from optparse import OptionParser
import os
import shlex
import socket
import sys
import subprocess

CERT_TEMPLATE_INFO = """
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

def run_command(cmd, verbose=True):
    if isinstance(cmd, str):
        cmd = shlex.split(cmd.encode('ascii', 'ignore'))
    if verbose:
        print "Running: %s" % (cmd)
    handle = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out_msg, err_msg = handle.communicate(None)
    if handle.returncode != 0:
        print "Error running: %s" % (cmd)
        print "stdout:\n%s" % (out_msg)
        print "stderr:\n%s" % (err_msg)
        return False
    return True, out_msg, err_msg

def write_template(output_name, template, hostname=None):
    if not hostname:
        hostname = socket.gethostname()
    out_file = open(output_name, "w")
    try:
        data = template.replace("REPLACE_COMMON_NAME", hostname)
        out_file.write(data)
        return True
    finally:
        out_file.close()
    return False

def create_ca(ca_key_name, ca_cert_name, config_file):
    if not os.path.exists(ca_key_name):
        cmd = "openssl genrsa -out %s 2048" % (ca_key_name)
        if not run_command(cmd):
            return False
    if not os.path.exists(ca_cert_name):
        cmd = ("openssl req -new -x509 -days 365 -key %s -out %s -config %s") % (ca_key_name, ca_cert_name, config_file)
        if not run_command(cmd):
            return False
    return True


if __name__ == "__main__":
    parser = OptionParser(description=
        "Helper utility to create certs for repository authentication")
    parser.add_option('--dir', action='store',
                help='Output directory to store certs', default='certs')
    parser.add_option('--ca_key', action='store', 
                help='CA key filename', default="Pulp_CA.key")
    parser.add_option('--ca_cert', action='store', 
                help='CA cert filename', default="Pulp_CA.crt")
    parser.add_option('--hostname', action='store',
                help='Hostname for Certs', default=None)
    (opts, args) = parser.parse_args()

    if not os.path.exists(opts.dir):
        os.makedirs(opts.dir)
    ca_key = os.path.join(opts.dir, opts.ca_key)
    ca_cert = os.path.join(opts.dir, opts.ca_cert)
    cert_config = os.path.join(opts.dir, "cert_config.cfg")

    if not write_template(output_name=cert_config, 
            template=CERT_TEMPLATE_INFO, hostname=opts.hostname):
        print "Failed to create cert configuration file"
        sys.exit(1)
    if not create_ca(ca_key, ca_cert, cert_config):
        print "Failed to create CA key/cert"
        sys.exit(1)

    print "CA Key: %s" % (ca_key)
    print "CA Cert: %s" % (ca_cert)

