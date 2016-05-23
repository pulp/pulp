from pulp.common import dateutils
from pulp.server.db.connection import get_collection


def migrate(*args, **kwargs):
    """
    Add last_updated and last_override_config to the distributor collection.
    """
    updated_key = 'last_updated'
    config_key = 'last_override_config'
    collection = get_collection('repo_distributors')
    for distributor in collection.find():
        if config_key not in distributor.keys():
            distributor[config_key] = {}

        if updated_key in distributor.keys():
            continue
        elif 'last_publish' in distributor.keys():
            distributor[updated_key] = distributor['last_publish']
        else:
            distributor[updated_key] = dateutils.now_utc_datetime_with_tzinfo()

        collection.save(distributor)
