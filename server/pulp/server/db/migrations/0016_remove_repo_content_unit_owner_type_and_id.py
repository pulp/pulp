"""
This migration loads the content types into the database. Part of the process includes dropping
of search indexes and their recreation.
"""
import logging

from pulp.server.db import connection

_logger = logging.getLogger(__name__)


def migrate(*args, **kwargs):
    """
    Perform the migration as described in this module's docblock.

    :param args:   unused
    :type  args:   list
    :param kwargs: unused
    :type  kwargs: dict
    """
    db = connection.get_database()

    # If 'repo_content_units' is not defined we don't need to do anything
    if 'repo_content_units' not in db.collection_names():
        return

    collection = db['repo_content_units']
    # Don't check whether we should run based on the index as that may have been cleared out
    # by a different migration
    if collection.find_one({'owner_type': {'$exists': True}}):
        remove_duplicates(collection)

        _logger.info("Removing unused fields (owner_type, owner_id) from repo_content_units")
        collection.update({}, {'$unset': {'owner_type': "", 'owner_id': ''}}, multi=True)

    index_info = collection.index_information()
    if "repo_id_-1_unit_type_id_-1_unit_id_-1_owner_type_-1_owner_id_-1" in index_info:
        _logger.info("Dropping the uniqueness index that included the owner_type & owner_id")
        collection.drop_index("repo_id_-1_unit_type_id_-1_unit_id_-1_owner_type_-1_owner_id_-1")


def remove_duplicates(collection):
    """
    Remove entries from the repo_content_units collection that would be duplicates
    after the owner_type and owner_id fields are removed. Always remove older
    entries so that incremental publishing will not be affected

    :param collection: a reference to the repo_content_units collection
    :type collection: pymongo.collection.collection
    """
    # Ensure that we have an appropriate index to perform the removal
    _logger.info("Creating index to assist with removal of duplicates")
    index = ['repo_id', 'unit_type_id', 'unit_id', 'updated']
    collection.ensure_index([(i, -1) for i in index])

    _logger.info("Removing duplicate repo_content_units")
    units_to_remove = []
    last_unit = {"repo_id": None, "unit_type_id": None, "unit_id": None}
    for unit in collection.find(sort=[('repo_id', 1), ('unit_type_id', 1),
                                      ('unit_id', 1), ('updated', 1)]):
        if last_unit['repo_id'] == unit['repo_id'] and \
                last_unit['unit_type_id'] == unit['unit_type_id'] and \
                last_unit['unit_id'] == unit['unit_id']:
            units_to_remove.append(last_unit['_id'])

        # batch up groups of 100 to so that this will run faster
        if len(units_to_remove) > 100:
            collection.remove({'_id': {'$in': units_to_remove}})
            units_to_remove = []
        last_unit = unit

    if units_to_remove:
        collection.remove({'_id': {'$in': units_to_remove}})

    collection.drop_index('repo_id_-1_unit_type_id_-1_unit_id_-1_updated_-1')
