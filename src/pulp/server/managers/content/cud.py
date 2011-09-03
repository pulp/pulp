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

from pulp.server.content.types import database as content_types_db
from pulp.server.managers.content.exceptions import ContentUnitNotFound


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
        unit_model = {'_id': unit_id}
        unit_model.update(unit_metadata)
        collection.insert(unit_model)
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
        content_unit = collection.find_one({'_id': unit_id})
        if content_unit is None:
            raise ContentUnitNotFound()
        content_unit = dict(content_unit)
        content_unit.update(unit_metadata_delta)
        collection.save(content_unit)

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
        collection.remove({'_id': unit_id})
