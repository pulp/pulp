#!/usr/bin/env python

import sys
from pulp.client import server
from pulp.api.repository import RepositoryAPI
from pulp.client.config import Config
import time


_cfg = Config()

if __name__ == "__main__":
    host = _cfg.server.host or 'localhost.localdomain'
    port = _cfg.server.port or '443'
    scheme = _cfg.server.scheme or 'https'
    path = _cfg.server.path or '/pulp/api'

    s = server.PulpServer(host, int(port), scheme, path)
    s.set_basic_auth_credentials("admin", "admin")
    server.set_active_server(s)
    if len(sys.argv) < 2:
        print "Please re-run with a repository id"
        sys.exit()
    repoid = sys.argv[1]
    print "Will sync repository [%s]" % repoid
    rapi = RepositoryAPI()
    ret_vals = [rapi.sync(repoid) for x in range(0,200)]
    for v in ret_vals:
        print "<%s>" % v

