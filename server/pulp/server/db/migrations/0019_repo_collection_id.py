"""
This migration moves the `id` field of the repos collection into `repo_id`.
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
    collection = db['repos']
    collection.update({}, {"$rename": {"id": "repo_id"}})
    collection.drop_index("id_-1")
