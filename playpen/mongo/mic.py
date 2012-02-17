"""
Quick Mongo DB Interactive Client for playing with mongo in python.
"""

import pymongo
from pymongo.collection import Collection
from pymongo.son_manipulator import AutoReference, NamespaceInjector


_connection = None
_db = None

# client api -------------------------------------------------------------------

def connect(db_name='pulp_database'):
    """
    Connect to a test database.
    Optional argument, db_name, specifies the name of the database.
    """
    global _connection, _db
    _connection = pymongo.Connection()
    _db = getattr(_connection, db_name)
    _db.add_son_manipulator(NamespaceInjector())
    _db.add_son_manipulator(AutoReference(_db))
    

def clean():
    """
    Drop all user-created collections in the database.
    """
    for name in _db.collection_names():
        if name.startswith(u'system.'):
            continue
        _db.drop_collection(name)


def collection(name, unique_indices=None, search_indicies=None):
    """
    Get a collection corresponding to the given name.
    Indice arguments must be a list of (index or indices tuple, direction)
    tuples. The same format accepted by Collection.ensure_index.
    """
    c = Collection(_db, name)
    if unique_indices:
        c.ensure_index(unique_indices, unique=True, background=True)
    if search_indicies:
        c.ensure_index(search_indicies, unique=False, background=True)
    return c

