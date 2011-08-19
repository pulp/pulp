#!/usr/bin/env python

# Reference: Blog post from Jason Dobies
# http://blog.pulpproject.org/2011/05/23/configuring-the-pulp-server-for-ssl/
# http://blog.pulpproject.org/2011/05/18/pulp-protected-repositories/

import os
import sys

from base import run_command, get_parser, update_openssl_config, add_hostname_option

def get_hostname():
    return socket.gethostname()

def create_server_key(server_key):
    cmd = "openssl genrsa -out %s 2048" % (server_key)
    return run_command(cmd)

def create_server_csr(server_key, csr_config, csr):
    # Maybe we can use -subj and not worry about the config file
    # http://onlamp.com/onlamp/2008/03/04/step-by-step-configuring-ssl-under-apache.html
    # -subj '/O=Company/OU=Department/CN=www.example.com'
    # http://www.bluequartz.us/phpBB2/viewtopic.php?p=397812&sid=208a45f412493be951cc3998569d8344
    # SUBJECT = /C=US/ST=OR/L=Portland/O=Our Organization  
    cmd = "openssl req -new -key %s -out %s -config %s" % (server_key, csr, csr_config)
    return run_command(cmd)

def create_server_cert(server_cert, server_csr, ca_cert, ca_key, ca_serial):
    cmd = "openssl x509 -req -days 365 -CA %s -CAkey %s -in %s -out %s -CAserial %s" \
            % (ca_cert, ca_key, server_csr, server_cert, ca_serial)
    if not os.path.exists(ca_serial):
        cmd = cmd + " -CAcreateserial"
    return run_command(cmd)

if __name__ == "__main__":
    parser = get_parser(limit_options=["ssl_conf_server_template", "ssl_conf_server", "server_key",
        "server_cert", "server_csr", "ca_key", "ca_cert", "ca_serial"])
    parser = add_hostname_option(parser)
    (opts, args) = parser.parse_args()

    ssl_conf_server_template = opts.ssl_conf_server_template
    ssl_conf_server = opts.ssl_conf_server
    hostname = opts.hostname
    server_key = opts.server_key
    server_cert = opts.server_cert
    server_csr = opts.server_csr
    ca_key = opts.ca_key
    ca_cert = opts.ca_cert
    ca_serial = opts.ca_serial

    if not update_openssl_config(ssl_conf_server_template, ssl_conf_server, hostname):
        print "Failed to create cert configuration file"
        sys.exit(1)

    if not create_server_key(server_key):
        print "Failed to create server key"
        sys.exit(1)

    if not create_server_csr(server_key, ssl_conf_server, server_csr):
        print "Failed to create server csr"
        sys.exit(1)

    if not create_server_cert(server_cert, server_csr, ca_cert, ca_key, ca_serial):
        print "Failed to create server cert"
        sys.exit(1)

    print "Server Cert: %s" % (server_cert)
    print "Server Key: %s" % (server_key)
