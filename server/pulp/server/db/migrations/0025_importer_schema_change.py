from pulp.common import dateutils
from pulp.server.db.connection import get_collection


def migrate(*args, **kwargs):
    """
    Add last_updated and last_override_config to the importer collection.
    """
    updated_key = 'last_updated'
    config_key = 'last_override_config'
    collection = get_collection('repo_importers')
    for importer in collection.find():
        if config_key not in importer.keys():
            importer[config_key] = {}

        if updated_key in importer.keys():
            continue
        elif 'last_sync' in importer.keys():
            importer[updated_key] = dateutils.parse_iso8601_datetime(importer['last_sync'])
        else:
            importer[updated_key] = dateutils.now_utc_datetime_with_tzinfo()

        collection.save(importer)
