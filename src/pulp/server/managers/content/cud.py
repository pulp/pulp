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

import uuid
from gettext import gettext as _

from pulp.server.content.types import database as content_types_db
from pulp.server.managers.content.exception import (
    ContentTypeNotFound, ContentUnitNotFound)


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
        unit_doc = {'_id': unit_id, '_content_type_id': content_type}
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

    def link_child_content_unit(self, parent_type, parent_id, child_type, child_ids):
        """
        Link children content units to a parent.
        @param parent_type: unique id of the parent content collection
        @type parent_type: str
        @param parent_id: unique id of the parent content unit
        @type parent_id: str
        @param child_type: unique id of the child content collection
        @type child_type: str
        @param child_ids: list of unique ids of child content units
        @types child_ids: tuple of list
        """
        collection = content_types_db.type_units_collection(parent_type)
        parent = collection.find_one({'_id': parent_id})
        if parent is None:
            msg = _('%(t)s content unit with id %(p) not found')
            raise ContentTypeNotFound(msg % {'t': parent_type, 'p': parent_id})
        # TODO validate the child type can be associated with the parent
        # XXX validate the child actually exists?
        children = parent.setdefault('_%s_children' % child_type, [])
        children.extend(child_ids)
        collection.update({'_id': parent_id}, parent, safe=True)

    def unlink_child_content_units(self, parent_type, parent_id, child_type, child_ids):
        """
        Unlink children content units from a parent.
        @param parent_type: unique id of the parent content collection
        @type parent_type: str
        @param parent_id: unique id of the parent content unit
        @type parent_id: str
        @param child_type: unique id of the child content collection
        @type child_type: str
        @param child_ids: list of unique ids of child content units
        @types child_ids: tuple of list
        """
        collection = content_types_db.type_units_collection(parent_type)
        parent = collection.find_one({'_id': parent_id})
        if parent is None:
            msg = _('%(t)s content unit with id %(p) not found')
            raise ContentTypeNotFound(msg % {'t': parent_type, 'p': parent_id})
        key = '_%s_children' % child_type
        children = set(parent.get(key, []))
        parent[key] = list(children.difference(child_ids))
        collection.update({'_id': parent_id}, parent, safe=True)
