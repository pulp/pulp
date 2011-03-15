#!/usr/bin/env python

import sys
import time
from pymongo import Connection
from pymongo.son_manipulator import AutoReference, NamespaceInjector
from optparse import OptionParser


def get_blob(size):
    blob = ""
    for index in range (0,size):
        blob += "a"
    return blob

def clear_data(db):
    print "db.name = %s" % (db.name)
    for name in db.collection_names():
        if name != "system.indexes":
            db.drop_collection(name)

def load_data(db, count=10000, blob_size=16*1024):
    for index in range(0, count):
        if (index % 100) == 0:
            print "Creating data for: %s/%s" % (index, count)
        obj = {}
        obj["name"] = "name_%s" % (index)
        obj["epoch"] = "%s" % (index % 2)
        obj["version"] = "%s" % (index % 100)
        obj["release"] = "%s" % (index % 10)
        obj["arch"] = "x86_64"
        blob = get_blob(blob_size)
        obj["extra1"] = blob
        obj["extra2"] = blob
        obj["extra3"] = blob
        obj["extra4"] = blob
        obj["extra5"] = blob
        obj["extra6"] = blob
        obj["extra7"] = blob
        obj["extra8"] = blob
        obj["extra9"] = blob
        obj["extra10"] = blob
        db.packages.save(obj, safe=True)

def run_query(db, count=1):
    q = []
    for index in range(0, count):
        obj = {}
        obj["name"] = "name_%s" % (index)
        obj["epoch"] = "%s" % (index % 2)
        obj["version"] = "%s" % (index % 100)
        obj["release"] = "%s" % (index % 10)
        obj["arch"] = "x86_64"
        q.append(obj)
    return (q, db.packages.find({"$or":q}))


if __name__ == "__main__":
    parser = OptionParser(usage="%prog [OPTIONS]", description="Test how dbrefs look")
    parser.add_option('--clear', action='store_true', 
                help='Clear data', default=False)
    parser.add_option('-l', '--load', action='store_true', 
                help='Load data', default=False)
    parser.add_option('-s', '--size', action='store', 
                help='Size of elements in $or query', default="10")
    parser.add_option('-v', '--verbose', action='store_true', 
                help='Verbose Flag', default=False)
    options, args = parser.parse_args()

    connection = Connection()
    db = connection.pulp_playpen
    db.add_son_manipulator(NamespaceInjector())
    db.add_son_manipulator(AutoReference(db))

    if options.clear:
        print "Test data has been cleared from: %s" % (db.name)
        clear_data(db)
        sys.exit(0)

    if options.load:
        load_data(db)
        print "Test data has been loaded into: %s" % (db.name)
        sys.exit(0)

    start = time.time()
    query, result = run_query(db, count=int(options.size))
    if options.verbose:
        print "Results:"
        for index, r in enumerate(result):
            print "%s:  %s" % (index, r)
        print "Query = [%s]" % (query)
    unused_list = [r for r in result]
    r2 = list(result)
    print "Query ran in %s seconds" % (time.time() - start)
    print "Results = %s" % (result.count()) 
