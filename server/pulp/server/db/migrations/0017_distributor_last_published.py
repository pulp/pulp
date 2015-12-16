from pulp.common.dateutils import parse_iso8601_datetime
from pulp.server.db.connection import get_collection


def migrate(*args, **kwargs):
    """
    Convert last_published iso8601 string to native date object.
    """
    key = 'last_publish'
    collection = get_collection('repo_distributors')
    for distributor in collection.find():
        last_publish = distributor[key]
        if not isinstance(last_publish, basestring):
            # already migrated
            continue
        distributor[key] = parse_iso8601_datetime(last_publish)
        collection.save(distributor)
