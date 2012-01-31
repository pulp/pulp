#!/usr/bin/env python

import sys
from base import get_parser, run_command, add_hostname_option

if __name__ == "__main__":
    parser = get_parser(limit_options=["ca_key", "ca_cert", "client_cert", "client_key"])
    parser = add_hostname_option(parser)
    opts, args = parser.parse_args()

    ca_cert = opts.ca_cert
    client_cert = opts.client_cert
    client_key = opts.client_key
    hostname = opts.hostname

    url = "https://%s/pulp/repos/repos/pulp/pulp/fedora-15/i386/repodata/repomd.xml" % (hostname)
    cmd = "curl --cacert %s --cert %s --key %s %s" % (ca_cert, client_cert, client_key, url)
    result = run_command(cmd)
    if result:
        state, out, err = result
        print "%s" % (out)
        print "%s" % (err)
