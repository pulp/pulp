import uuid

from pulp.common import dateutils
from pulp.plugins.types import database as content_types_db
from pulp.server.exceptions import InvalidValue


class ContentManager(object):
    """
    Create, update and delete operations for content in pulp.
    """

    def add_content_unit(self, content_type, unit_id, unit_metadata):
        """
        Add a content unit and its metadata to the corresponding pulp db
        collection.
        @param content_type: unique id of content collection
        @type content_type: str
        @param unit_id: unique id of content unit, None means to generate id
        @type unit_id: str or None
        @param unit_metadata: content unit metadata
        @type unit_metadata: dict
        @return: unit id, useful if it was generated
        @rtype: str
        """
        collection = content_types_db.type_units_collection(content_type)
        if unit_id is None:
            unit_id = str(uuid.uuid4())
        unit_doc = {
            '_id': unit_id,
            '_content_type_id': content_type,
            '_last_updated': dateutils.now_utc_timestamp()
        }
        unit_doc.update(unit_metadata)
        collection.insert(unit_doc, safe=True)
        return unit_id

    def update_content_unit(self, content_type, unit_id, unit_metadata_delta):
        """
        Update a content unit's stored metadata.
        @param content_type: unique id of content collection
        @type content_type: str
        @param unit_id: unique id of content unit
        @type unit_id: str
        @param unit_metadata_delta: metadata fields that have changed
        @type unit_metadata_delta: dict
        """
        unit_metadata_delta['_last_updated'] = dateutils.now_utc_timestamp()
        collection = content_types_db.type_units_collection(content_type)
        collection.update({'_id': unit_id}, {'$set': unit_metadata_delta}, safe=True)

    def remove_content_unit(self, content_type, unit_id):
        """
        Remove a content unit and its metadata from the corresponding pulp db
        collection.
        @param content_type: unique id of content collection
        @type content_type: str
        @param unit_id: unique id of content unit
        @type unit_id: str
        """
        collection = content_types_db.type_units_collection(content_type)
        collection.remove({'_id': unit_id}, safe=True)

    def link_referenced_content_units(self, from_type, from_id, to_type, to_ids):
        """
        Link referenced content units.
        @param from_type: unique id of the parent content collection
        @type from_type: str
        @param from_id: unique id of the parent content unit
        @type from_id: str
        @param to_type: unique id of the child content collection
        @type to_type: str
        @param to_ids: list of unique ids of child content units
        @types child_ids: tuple of list
        """
        collection = content_types_db.type_units_collection(from_type)
        parent = collection.find_one({'_id': from_id})
        if parent is None:
            raise InvalidValue(['from_type'])
        parent_type_def = content_types_db.type_definition(from_type)
        if to_type not in parent_type_def['referenced_types']:
            raise Exception()
        children = parent.setdefault('_%s_references' % to_type, [])
        for id_ in to_ids:
            if id_ in children:
                continue
            children.append(id_)
        collection.update({'_id': from_id}, parent, safe=True)

    def unlink_referenced_content_units(self, from_type, from_id, to_type, to_ids):
        """
        Unlink referenced content units.
        @param from_type: unique id of the parent content collection
        @type from_type: str
        @param from_id: unique id of the parent content unit
        @type from_id: str
        @param to_type: unique id of the child content collection
        @type to_type: str
        @param to_ids: list of unique ids of child content units
        @types child_ids: tuple of list
        """
        collection = content_types_db.type_units_collection(from_type)
        parent = collection.find_one({'_id': from_id})
        if parent is None:
            raise InvalidValue(['from_type'])
        key = '_%s_references' % to_type
        children = set(parent.get(key, []))
        parent[key] = list(children.difference(to_ids))
        collection.update({'_id': from_id}, parent, safe=True)
