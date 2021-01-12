import pymongo

from pulp.server.db import connection


def migrate(*args, **kwargs):
    """
    Add an index on ContentUnit._last_updated, to allow ordering by update

    :param args:   unused
    :type  args:   list
    :param kwargs: unused
    :type  kwargs: dict
    """
    db = connection.get_database()
    # list_collections(filter=) isn't introduced until 3.6, alas
    for collname in db.collection_names():
        if collname.startswith("units_"):
            db[collname].create_index([("_last_updated", pymongo.DESCENDING)], background=False)
