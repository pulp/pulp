from pulp.common import dateutils
from pulp.server.db import connection


def migrate(*args, **kwargs):
    """
    Ensure all importers & distributors and associated results collections
    have their timestamp fields in UTC.
    """
    fields_to_update = [['repo_distributors', 'last_publish'],
                        ['repo_group_distributors', 'last_publish'],
                        ['repo_publish_results', 'started'],
                        ['repo_publish_results', 'completed'],
                        ['repo_group_publish_results', 'started'],
                        ['repo_group_publish_results', 'completed'],
                        ['repo_importers', 'last_sync'],
                        ['repo_sync_results', 'started'],
                        ['repo_sync_results', 'completed']
                        ]

    db = connection.get_database()
    collection_list = db.collection_names()
    for collection_name, field_name in fields_to_update:
        if collection_name in collection_list:
            update_time_to_utc_on_collection(collection_name, field_name)


def update_time_to_utc_on_collection(collection_name, field_name):
    """
    Update the iso8601 string representation of time in a field in a collection
    from time zone specific to UTC native

    :param collection_name: The name of the collection to update
    :type collection_name: str
    :param field_name: The name of the field within the collection that contains the timestamp
    :type field_name: str
    """
    collection = connection.get_collection(collection_name)
    for distributor in collection.find({field_name: {'$ne': None}}):
        time_str = distributor[field_name]
        time = dateutils.parse_iso8601_datetime(time_str)
        # only update if we are not UTC to begin with
        if time.tzinfo != dateutils.utc_tz():
            time_utc = dateutils.to_utc_datetime(time)
            distributor[field_name] = dateutils.format_iso8601_datetime(time_utc)
            collection.save(distributor, safe=True)
