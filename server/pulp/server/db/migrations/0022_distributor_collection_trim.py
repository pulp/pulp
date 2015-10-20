"""
This migration moves the `id` field of the repo_distributors collection into `distributor_id`.
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
    collection = db['repo_distributors']
    collection.update({}, {"$rename": {"id": "distributor_id"}}, multi=True)
    collection.update({}, {"$unset": {"scheduled_publishes": ""}}, multi=True)
    collection.drop_index("repo_id_-1_id_-1")
