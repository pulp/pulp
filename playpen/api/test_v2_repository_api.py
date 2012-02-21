#!/usr/bin/env python

import os
import sys
from pulp.gc_client.api import server
from pulp.gc_client.api.repository import RepositoryAPI
import time


if __name__ == "__main__":
    host = 'localhost.localdomain'

    pc = server.PulpConnection(host="localhost", username='admin', password='admin')
    server.set_active_server(pc)
    if len(sys.argv) < 2:
        print "Please re-run with a repository id"
        sys.exit()
    repoid = sys.argv[1]
    print "Will create repository [%s]" % repoid
    rapi = RepositoryAPI()
    ret_vals = rapi.create(id=repoid, display_name=repoid, description=repoid, notes={})
    print ret_vals

