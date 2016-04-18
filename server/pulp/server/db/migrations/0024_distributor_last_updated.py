from pulp.common import dateutils
from pulp.server.db.connection import get_collection


def migrate(*args, **kwargs):
    """
    Add last_updated to the distributor collection.
    """
    key = 'last_updated'
    collection = get_collection('repo_distributors')
    for distributor in collection.find():
        if key in distributor.keys():
            continue
        elif 'last_publish' in distributor.keys():
            distributor[key] = distributor['last_publish']
        else:
            distributor[key] = dateutils.now_utc_datetime_with_tzinfo()
        collection.save(distributor)
