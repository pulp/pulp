#!/usr/bin/env python

import os
import sys
from pulp.client import server
from pulp.client import utils
from pulp.client.api.service import ServiceAPI
from pulp.client.cli.base import PulpCLI
from pulp.client.config import Config

_cfg = Config()

if __name__ == "__main__":
    host = _cfg.server.host or 'localhost.localdomain'
    port = _cfg.server.port or '443'
    scheme = _cfg.server.scheme or 'https'
    path = _cfg.server.path or '/pulp/api'

    s = server.PulpServer(host, int(port), scheme, path)
    s.set_basic_auth_credentials("admin", "admin")
    server.set_active_server(s)
    
    sapi = ServiceAPI()
    if not len(sys.argv) > 2:
        print "Re-run with a CSV data file in format: filename,checksum"
        print "Example: %s <cvs data file> repo1 repo2 repo3" % (sys.argv[0])
        sys.exit(1)
    csv_file = sys.argv[1]
    repos = sys.argv[2:]
    csv_data = utils.parseCSV(csv_file)
    package_info = []
    for d in csv_data:
        filename = os.path.basename(d[0])
        checksum = d[1]
        package_info.append(((filename,checksum),repos))
    errors = sapi.associate_packages(package_info)
    if errors:
        print "Errors occurred"
        error_log = open("./error_log_package_associate", "w")
        for e in errors:
            error_log.write(e)
            error_log.write("\t %s" % (errors[e]))
            error_log.write("\n")
        error_log.close()
    else:
        print "Success, no errors occurred"
