from pulp.common.dateutils import parse_iso8601_datetime
from pulp.server.db.model.repository import RepoDistributor


def migrate(*args, **kwargs):
    """
    Convert last_published iso8601 string to native date object.
    """
    key = 'last_publish'
    collection = RepoDistributor.get_collection()
    for distributor in collection.find():
        last_publish = distributor[key]
        if not isinstance(last_publish, basestring):
            # already migrated
            continue
        distributor[key] = parse_iso8601_datetime(last_publish)
        collection.save(distributor, safe=True)
