#!/usr/bin/env python
import time
from pymongo import Connection
from pymongo.son_manipulator import AutoReference, NamespaceInjector
from optparse import OptionParser

import pulp.util
from pulp.api.package_version import PackageApi

if __name__ == "__main__":
    
    package_id = "pulp-test-package"
    checksum = "6bce3f26e1fc0fc52ac996f39c0d0e14fc26fb8077081d5b4dbfb6431b08aa9f"
    checksum_type = "sha256"
    filename = "pulp-test-package-0.3.1-1.fc11.x86_64.rpm"


    config = pulp.util.loadConfig("../../etc/pulp.conf")
    pApi = PackageApi(config)

    found = pApi.package(filename=filename, checksum_type=checksum_type, checksum=checksum)
    print "Lookup for %s, %s, %s yielded %s" % (filename, checksum_type, checksum, found)

    db = pApi.objectdb
    print "db = %s" % (db)
    found = db.find({"filename":filename})
    print "Search for all PV's with %s: %s" % (filename, found)
    for f in found:
        print f
    found = db.find()
    print "%s PV objects found with an open search" % (found.count())

    found = pApi.package()
    print "search with empty searchDict returned %s results" % (found.count())

