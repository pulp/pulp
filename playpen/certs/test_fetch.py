#!/usr/bin/env python

import sys
from base import get_parser, run_command

if __name__ == "__main__":
    parser = get_parser(limit_options=["ca_key", "ca_cert", "ent_cert", "ent_key"])
    opts, args = parser.parse_args()

    ca_cert = opts.ca_cert
    ent_cert = opts.ent_cert
    ent_key = opts.ent_key
    hostname = opts.hostname

    url = "https://%s/pulp/repos/repos/pulp/pulp/fedora-15/i386/repodata/repomd.xml" % (hostname)
    cmd = "curl --cacert %s --cert %s --key %s %s" % (ca_cert, ent_cert, ent_key, url)
    state, out, err = run_command(cmd)
    print "%s" % (out)
    print "%s" % (err)
