#!/bin/sh
mongo<<END
 use pulp_database;
 overall = db.stats();
 printjson(overall);
 coll_stats = db.getCollectionNames().map(function(c) {s = db[c].stats(); return s});
 sorted_coll_stats = coll_stats.sort(function(a,b) {return b.storageSize-a.storageSize;})
 printjson(sorted_coll_stats)
END

