from pulp.common import dateutils
from pulp.server.db.connection import get_collection


def migrate(*args, **kwargs):
    """
    Make sure last_updated field is set for every distributor.
    """
    updated_key = 'last_updated'
    collection = get_collection('repo_distributors')
    for distributor in collection.find():
        if distributor.get(updated_key) is None:
            distributor[updated_key] = dateutils.now_utc_datetime_with_tzinfo()
            collection.save(distributor)
