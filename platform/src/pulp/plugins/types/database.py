# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Responsible for the storage and retrieval of content types in the database.
This module covers both the ContentType collection itself as well as any
type-specific collections that exist to suit the type needs.
"""

import logging

from pymongo import ASCENDING

import pulp.server.db.connection as pulp_db
from pulp.server.db.model.content import ContentType

# -- constants ----------------------------------------------------------------

TYPE_COLLECTION_PREFIX = 'units_'

LOG = logging.getLogger(__name__)

# -- database exceptions ------------------------------------------------------

class UpdateFailed(Exception):
    """
    Indicates a call to update the database has failed for one or more type
    definitions. The instance will contain the definitions that were unable
    to be correctly installed into the database.
    """

    def __init__(self, type_definitions):
        Exception.__init__(self)
        self.type_definitions = type_definitions

    def __str__(self):
        return 'UpdateFailed [%s]' % ', '.join([t.id for t in self.type_definitions])


class MissingDefinitions(Exception):
    """
    Raised when one or more type collections previously existed in the database
    but were not present in an update call. The instance will contain a list
    of type IDs that were previously loaded but not in the subsequent update
    call.
    """

    def __init__(self, missing_type_ids):
        Exception.__init__(self)
        self.missing_type_ids = missing_type_ids

    def __str__(self):
        return 'MissingDefinitions [%s]' % ', '.join(self.missing_type_ids)

# -- public -------------------------------------------------------------------

def update_database(definitions, error_on_missing_definitions=False):
    """
    Brings the database up to date with the types defined in the given
    descriptors.

    @param definitions: set of all definitions
    @type  definitions: list of L{TypeDefinitions}

    @param error_on_missing_definitions: if True, an exception will be raised
           if there is one or more type collections already in the database
           that are not represented in the given descriptors; defaults to False
    @type  error_on_missing_definitions: bool
    """

    all_type_ids = [d.id for d in definitions]

    LOG.info('Updating the database with types [%s]' % ', '.join(all_type_ids))

    # Get a list of all type collections now so we can figure out which
    # previously existed but are not in the new list
    existing_type_names = [t[len(TYPE_COLLECTION_PREFIX):] for t in all_type_collection_names()]
    update_type_ids = [t.id for t in definitions]
    missing = set(existing_type_names) - set(update_type_ids)

    if len(missing) > 0:
        LOG.warn('Found the following type definitions that were not present in the update collection [%s]' % ', '.join(missing))

        if error_on_missing_definitions:
            raise MissingDefinitions(missing)

    # For each type definition, update the corresponding collection in the database
    error_defs = []

    for type_def in definitions:
        try:
            _create_or_update_type(type_def)
        except Exception:
            LOG.exception('Exception creating/updating collection for type [%s]' % type_def.id)
            error_defs.append(type_def)
            continue

        try:
            # May need to revisit if the recreation takes too long with large content sets
            _drop_indexes(type_def)
        except Exception:
            LOG.exception('Exception dropping indexes for type [%s]' % type_def.id)
            error_defs.append(type_def)
            continue

        try:
            _update_unit_key(type_def)
        except Exception:
            LOG.exception('Exception updating unit key for type [%s]' % type_def.id)
            error_defs.append(type_def)
            continue

        try:
            _update_search_indexes(type_def)
        except Exception:
            LOG.exception('Exception updating search indexes for type [%s]' % type_def.id)
            error_defs.append(type_def)
            continue

    if len(error_defs) > 0:
        raise UpdateFailed(error_defs)


def clean():
    """
    Purges the database of all types and their associated collections. This
    isn't really meant to be run from Pulp server code but rather as a utility
    for test cases.
    """

    LOG.info('Purging the database of all content type definitions and collections')

    # Search the database instead of just going on what's in the type listing
    # just in case they got out of sync
    database = pulp_db.database()
    all_collection_names = database.collection_names()
    type_collection_names = [n for n in all_collection_names if n.startswith(TYPE_COLLECTION_PREFIX)]
    for drop_me in type_collection_names:
        database.drop_collection(drop_me)

    # Purge the types collection of all entries
    type_collection = ContentType.get_collection()
    type_collection.remove(safe=True)


def type_units_collection(type_id):
    """
    Returns a reference to the collection used to store units of the given type.

    @param type_id: identifier for the type
    @type  type_id: str

    @return: database collection holding units of the given type
    @rtype:  L{pymongo.collection.Collection}
    """
    collection_name = unit_collection_name(type_id)
    collection = pulp_db.get_collection(collection_name, create=False)
    return collection


def all_type_ids():
    """
    @return: list of IDs for all types currently in the database; empty list
             if there are no IDs in the database
    @rtype:  list of str
    """

    collection = ContentType.get_collection()
    type_id_son = list(collection.find(fields={'id' : 1}))
    type_ids = [t['id'] for t in type_id_son]

    return type_ids


def all_type_collection_names():
    """
    @return: list of collection names for all types currently in the database
    @rtype:  list of str
    """

    collection = ContentType.get_collection()
    type_ids = list(collection.find(fields={'id' : 1}))

    type_collection_names = []
    for id in type_ids:
        type_collection_names.append(unit_collection_name(id['id']))

    return type_collection_names


def all_type_definitions():
    """
    @return: list of all type definitions in the database (mongo SON objects)
    @rtype:  list of dict
    """

    coll = ContentType.get_collection()
    types = list(coll.find())
    return types


def type_definition(type_id):
    """
    Return a type definition
    @param type_id: unique type id
    @type type_id: str
    @return: corresponding type definition, None if not found
    @rtype: SON or None
    """
    collection = ContentType.get_collection()
    type_ = collection.find_one({'id': type_id})
    return type_


def unit_collection_name(type_id):
    """
    Returns the name of the collection used to store units of the given type.

    @param type_id: identifies the type
    @type  type_id: str

    @return: name of the collection in the Pulp database
    @rtype:  str
    """
    return TYPE_COLLECTION_PREFIX + type_id


def type_units_unit_key(type_id):
    """
    Get the unit key for a given content type collection. If no type
    definition is found for the given ID, None is returned

    @param type_id: unique content type identifier
    @type type_id: str
    @return: list of indices that can uniquely identify a document in the
             content type collection
    @rtype: list of str or None
    """
    collection = ContentType.get_collection()
    type_def = collection.find_one({'id': type_id})
    if type_def is None:
        return None
    return type_def['unit_key']

# -- private -----------------------------------------------------------------

def _create_or_update_type(type_def):

    # Make sure a collection exists for the type
    database = pulp_db.database()
    collection_name = unit_collection_name(type_def.id)

    if collection_name not in database.collection_names():
        pulp_db.get_collection(collection_name, create=True)

    # Add or update an entry in the types list
    content_type_collection = ContentType.get_collection()
    content_type = ContentType(type_def.id, type_def.display_name, type_def.description,
                               type_def.unit_key, type_def.search_indexes, type_def.referenced_types)
    # no longer rely on _id = id
    existing_type = content_type_collection.find_one({'id': type_def.id}, fields=[])
    if existing_type is not None:
        content_type._id = existing_type['_id']
    # XXX this still causes a potential race condition when 2 users are updating the same type
    content_type_collection.save(content_type, safe=True)

def _update_indexes(type_def, unique):

    collection_name = unit_collection_name(type_def.id)
    collection = pulp_db.get_collection(collection_name, create=False)

    if unique:
        index_list = [type_def.unit_key] # treat the key as a compound key
    else:
        index_list = type_def.search_indexes

    if index_list is None:
        return

    for index in index_list:

        if isinstance(index, (list, tuple)):
            LOG.info('Ensuring index [%s] (unique: %s) on type definition [%s]' % (', '.join(index), unique, type_def.id))
            mongo_index = _create_index_keypair(index)
        else:
            LOG.info('Ensuring index [%s] (unique: %s) on type definition [%s]' % (index, unique, type_def.id))
            mongo_index = index

        index_name = collection.ensure_index(mongo_index, unique=unique, drop_dups=False)

        if index_name is not None:
            LOG.info('Index [%s] created on type definition [%s]' % (index_name, type_def.id))
        else:
            LOG.info('Index already existed on type definition [%s]' % type_def.id)


def _update_unit_key(type_def):
    _update_indexes(type_def, True)


def _update_search_indexes(type_def):
    _update_indexes(type_def, False)


def _drop_indexes(type_def):
    collection_name = unit_collection_name(type_def.id)
    collection = pulp_db.get_collection(collection_name, create=False)
    collection.drop_indexes()


def _create_index_keypair(index):
    """
    When specifying a compound index (more than one key), the direction
    must be specified along with each key. Ultimately the direction should
    be specified in the descriptor, but for now assume all keys in a compound
    index should be sorted ascending.

    @param index: a compound index (made up of more than one key)
    @type  index: list of str
    """

    mongo_index = [(k, ASCENDING) for k in index]
    return mongo_index
