#!/usr/bin/env python
import time
from pymongo import Connection


connection = Connection()
db = connection.pulp_database
while True:
    a = time.time()
    repo_cursor = db.repos.find()
    b = time.time()
    result = list(repo_cursor)
    c = time.time()
    time_initial_query = b-a
    time_traverse_cursor = c-b

    print "%s: Total %s seconds, db.repositories.find() took %s seconds.  list(result) took %s seconds, %s%% of operation.  %s items  " % (time.ctime(), (time_initial_query + time_traverse_cursor), time_initial_query, time_traverse_cursor, (float(time_traverse_cursor)/(time_initial_query+time_traverse_cursor)), len(result))
    time.sleep(2)

