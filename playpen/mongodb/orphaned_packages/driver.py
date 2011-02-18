#!/usr/bin/env python

from pymongo import Connection
from bson.code import Code

connection = Connection()
db = connection.pulp_database

m = Code(open("map.js", "r").read())
r = Code(open("reduce.js", "r").read())

coll = db.packages.map_reduce(m,r)
results = coll.find()
print results[0]
results = coll.find({"value.count":0})
print "%s results found " % (results.count())
orphanids = [x["value"]["package_id"] for x in results]
results = db.packages.find({"id":{"$in":orphanids}}, {"id":1, "filename":1, "checksum":1})
for index, r in enumerate(results):
    print "Id: %s\t Filename: %s \tChecksum: %s" % (r["id"], r["filename"], r["checksum"])
    if index >= 15:
        print "%s more matches available...." % (results.count()-index)
        break
