 events = []
 cursor = db.events.find();
 cursor.forEach(function(c) {
    c.bsonsize = Object.bsonsize(c)
    events.push(c)
 })
 sorted_events = events.sort(function(a,b) {
     return b.bsonsize-a.bsonsize;
 })
 print(cursor.count() + " events exist taking up " + db.events.totalSize())
 print("Largest event is " + sorted_events[0].bsonsize + "\n")
 printjson(sorted_events[0])
 print("Second largest event is " + sorted_events[1].bsonsize + "\n")
 printjson(sorted_events[1])

