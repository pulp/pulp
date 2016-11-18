import datetime

import isodate

from pulp.server.db.connection import get_collection


def migrate(*args, **kwargs):
    """
    Add last_updated and last_override_config to the importer collection.
    """
    updated_key = 'last_updated'
    config_key = 'last_override_config'
    collection = get_collection('repo_importers')

    for importer in collection.find():
        modified = False

        if config_key not in importer:
            importer[config_key] = {}
            modified = True

        # If the key doesn't exist, or does exist but has no value, set it based on the
        # last sync time, if possible. Otherwise, set it to now.
        if not importer.get(updated_key, None):
            try:
                importer[updated_key] = isodate.parse_datetime(importer['last_sync'])
            # The attribute doesn't exist, or parsing failed. It's safe to set a newer timestamp.
            except:
                importer[updated_key] = datetime.datetime.now(tz=isodate.UTC)
            modified = True

        if modified:
            collection.save(importer)
