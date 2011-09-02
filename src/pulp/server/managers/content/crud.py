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

import os
import uuid

from pulp.server.constants import LOCAL_STORAGE
from pulp.server.content.types import database as content_types_db
from pulp.server.pexceptions import PulpException


class ContentUnitNotFound(PulpException):
    pass


class ContentTypeNotFound(PulpException):
    pass


class ContentManager(object):
    """
    """

    def add_content_unit(self, content_type, unit_id, unit_metadata):
        """
        """
        collection = content_types_db.type_units_collection(content_type)
        if unit_id is None:
            unit_id = str(uuid.uuid4())
        unit_model = {'_id': unit_id}
        unit_model.update(unit_metadata)
        collection.insert(unit_model)
        return unit_id

    def list_content_units(self, content_type, db_spec=None, model_fields=None, start=0, limit=None):
        """
        """
        collection = content_types_db.type_units_collection(content_type)
        cursor = collection.find(db_spec, fields=model_fields)
        if start > 0:
            cursor.skip(start)
        if limit is not None:
            cursor.limit(limit)
        return tuple(cursor)

    def get_content_unit_by_keys(self, content_type, content_keys):
        """
        """
        units = self.get_multiple_units_by_keys(content_type, (content_keys,))
        if not units:
            raise ContentUnitNotFound()
        return units[0]

    def get_content_unit_by_id(self, content_type, content_id):
        """
        """
        units = self.get_multiple_units_by_ids(content_type, (content_id,))
        if not units:
            raise ContentUnitNotFound()
        return units[0]

    def get_multiple_units_by_keys(self, content_type, unit_keys, model_fields=None):
        """
        """
        collection = content_types_db.type_units_collection(content_type)
        spec = _build_muti_keys_spec(content_type, unit_keys)
        cursor = collection.find(spec, fields=model_fields)
        return tuple(cursor)

    def get_multiple_units_by_ids(self, content_type, unit_ids, model_fields=None):
        """
        """
        collection = content_types_db.type_units_collection(content_type)
        cursor = collection.find({'_id': {'$in': unit_ids}}, fields=model_fields)
        return tuple(cursor)

    def get_content_unit_keys(self, content_type, unit_ids):
        """
        """
        key_fields = content_types_db.type_units_unique_indexes(content_type)
        if key_fields is None:
            raise ContentTypeNotFound()
        collection = content_types_db.type_units_collection(content_type)
        cursor = collection.find({'_id': {'$in': unit_ids}}, fields=key_fields)
        if cursor.count() == 0:
            return tuple()
        return tuple(cursor)

    def get_content_unit_ids(self, content_type, unit_keys):
        """
        """
        collection = content_types_db.type_units_collection(content_type)
        spec = _build_muti_keys_spec(content_type, unit_keys)
        cursor = collection.find(spec, fields=['_id'])
        return tuple(cursor)

    def get_root_content_dir(self, content_type):
        """
        """
        # I'm paritioning the content on the file system based on content type
        return os.path.join(LOCAL_STORAGE, content_type)

    def request_content_unit_file_path(self, content_type, relative_path):
        """
        """
        return os.path.join(self.get_root_content_dir(content_type), relative_path)

    def update_content_unit(self, content_type, unit_id, unit_metadata_delta):
        """
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
        """
        collection = content_types_db.type_units_collection(content_type)
        collection.remove({'_id': unit_id})

# utility methods --------------------------------------------------------------

def _build_muti_keys_spec(content_type, unit_keys):
    """
    """
    key_fields = content_types_db.type_units_unique_indexes(content_type)
    spec_template = dict([(f, set()) for f in key_fields])
    for key in unit_keys:
        found_k = 0
        for k, v in key.items():
            if k not in spec_template:
                raise ValueError()
            spec_template[k].add(v)
            found_k += 1
        if found_k != len(key_fields):
            raise ValueError()
    return dict([(k, {'$in': list(v)}) for k, v in spec_template])
