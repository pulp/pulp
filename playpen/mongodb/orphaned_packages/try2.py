#!/usr/bin/env python
from pymongo import Connection

db = Connection().pulp_database
rpids = db.repos.find({}, {"packages":1})
repo_pkgids = set()
for r in rpids:
    repo_pkgids.update(r["packages"])
print "%s repo_package_ids were found" % (len(repo_pkgids))
results = db.packages.find({}, {"id":1})
pkgids = set([x["id"] for x in results])
print "%s package ids were found" % (len(pkgids))
diff = pkgids.difference(repo_pkgids)
print "%s orphaned packages" % (len(diff))
