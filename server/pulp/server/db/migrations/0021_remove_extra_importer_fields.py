"""
This migration removes the `id` and `scheduled_syncs` fields from the importers collection.
"""
from pulp.server.db import connection


def migrate(*args, **kwargs):
    """
    Perform the migration as described in this module's docblock.

    :param args:   unused
    :type  args:   list
    :param kwargs: unused
    :type  kwargs: dict
    """
    db = connection.get_database()
    collection = db['repo_importers']
    collection.update({}, {"$unset": {"id": True}}, multi=True)
    collection.drop_index("repo_id_-1_id_-1")
    collection.update({}, {"$unset": {"scheduled_syncs": ""}}, multi=True)
