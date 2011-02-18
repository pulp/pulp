#!/usr/bin/env python
from pymongo import Connection

db = Connection().pulp_database
rpids = db.repos.find({}, {"packages":1})
repo_pkgids = set()
for r in rpids:
    #print r["_id"]
    repo_pkgids.update(r["packages"])
print "How many repo_package_ids have we built up: %s" % (len(repo_pkgids))
results = db.packages.find({"id":{"$nin":list(repo_pkgids)}})
print "Found %s results" % (results.count())
for r in results:
    print r
#print results.count()
#print "len(results) = %s" % (results.count())
#for r in results:
#    print r
