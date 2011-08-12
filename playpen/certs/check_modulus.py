#!/usr/bin/env python

import os
import sys
from create_ca import run_command
from create_content_cert import parse_args

def check_modulus(key, cert):
    cert_modulus = ""
    cmd = "openssl x509 -noout -modulus -in %s " % (cert)
    status = run_command(cmd)
    if status:
        state, out, err = status
        cert_modulus = out
    key_modulus = ""
    cmd = "openssl rsa -noout -modulus -in %s " % (key)
    status = run_command(cmd)
    if status:
        state, out, err = status
        key_modulus = out
    if cert_modulus and key_modulus and cert_modulus == key_modulus:
        return True
    return False

if __name__ == "__main__":
    opts, args = parse_args()

    ent_key = os.path.join(opts.dir, opts.ent_key)
    ent_cert = os.path.join(opts.dir, opts.ent_cert)
    ca_key = os.path.join(opts.dir, opts.ca_key)
    ca_cert = os.path.join(opts.dir, opts.ca_cert)

    #Check the matching server/key.  They should have the same modulus
    if not check_modulus(ca_key, ca_cert):
        print 'Error, modulus for "%s" and "%s" are different' % (ca_key,ca_cert)
        sys.exit(1)
    if not check_modulus(ent_key, ent_cert):
        print 'Error, modulus for "%s" and "%s" are different' % (ent_key,ent_cert)
        sys.exit(1)
    print "Checks passed"
