#!/usr/bin/env python
#http://api.mongodb.org/python/1.9%2B/examples/map_reduce.html?highlight=map%20reduce

from pymongo import Connection
from bson.code import Code

db = Connection().test_map_reduce_example
db.things.remove()
db.things.insert({"x": 1, "tags": ["dog", "cat"]})
db.things.insert({"x": 2, "tags": ["cat"]})
db.things.insert({"x": 3, "tags": ["mouse", "cat", "dog"]})
db.things.insert({"x": 4, "tags": []})

m = Code(
    "function () {"
    "  this.tags.forEach(function(z) {"
    "    emit(z, 1);"
    "  });"
    "}")

r = Code(
    "function (key, values) {"
    "  var total = 0;"
    "  for (var i = 0; i < values.length; i++) {"
    "    total += values[i];"
    "  }"
    "  return total;"
    "}")

result = db.things.map_reduce(m,r, "example")
for doc in result.find():
    print doc

