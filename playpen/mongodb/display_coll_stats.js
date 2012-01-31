 overall = db.stats();
 coll_stats = db.getCollectionNames().map(function(c) {s = db[c].stats(); return s});
 sorted_coll_stats = coll_stats.sort(function(a,b) {return b.storageSize-a.storageSize;});
 print ("Per Collection Information:\n")
 printjson(sorted_coll_stats);
 print("Overall:\n");
 printjson(overall);
 sorted_coll_stats.forEach(function(c) { 
     print(c.ns + ": NumObjects: " + c.count + 
         ", AvgObjSize: " + c.avgObjSize + 
         ", StorageSize: " + c.storageSize + 
         ", IndexSize: " + c.totalIndexSize);
 })

