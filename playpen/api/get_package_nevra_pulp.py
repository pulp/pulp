#!/usr/bin/env python

import sys
import time
from pymongo import Connection
from pymongo.son_manipulator import AutoReference, NamespaceInjector
from optparse import OptionParser

def get_nevras(num_items):
    q = []
    # Grab whatever we can from pulp DB
    # we dont care specifically what is grabbed
    result = db.packages.find().limit(num_items)
    for r in result:
        obj = {}
        for k in ['name', 'epoch', 'version', 'release', 'arch']:
            obj[k] = r[k]
        q.append(obj)
    return q

if __name__ == "__main__":
    parser = OptionParser(usage="%prog [OPTIONS]", description="Test how dbrefs look")
    parser.add_option('-s', '--size', action='store', 
                help='Size of elements in $or query', default="10")
    parser.add_option('-v', '--verbose', action='store_true', 
                help='Verbose Flag', default=False)
    options, args = parser.parse_args()

    connection = Connection()
    db = connection.pulp_database
    db.add_son_manipulator(NamespaceInjector())
    db.add_son_manipulator(AutoReference(db))

    num_items = int(options.size)
    nevras = get_nevras(num_items)
    if len(nevras) < num_items:
        print "Warning: Couldn't find %s items to query with, only found %s" % (num_items, len(nevras))

    start = time.time()
    results = db.packages.find({"$or":nevras})
    if options.verbose:
        print "Results:"
        for index, r in enumerate(result):
            print "%s:  %s" % (index, r)
        print "Query = [%s]" % (query)
    #r2 = list(results)
    print "Results = %s" % (results.count()) 
    print "Query ran in %s seconds" % (time.time() - start)
