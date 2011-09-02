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


class ContentManager(object):
    """
    """

    def add_content_unit(self, content_type, unit_id, unit_metadata):
        """
        """
        # XXX we should store the TypeDefinitions in their own collection in
        # the db so that we can validate the metadata
        collection = _get_type_collection(content_type)
        if unit_id is None:
            unit_id = str(uuid.uuid4())
        unit_model = {'_id': unit_id}
        unit_model.update(unit_metadata)
        collection.insert(unit_model)

    def list_content_units(self, content_type, db_spec=None, model_fields=None):
        """
        """
        collection = _get_type_collection(content_type)
        cursor = collection.find(db_spec, fields=model_fields)
        # delima: retrun the cursor itself?
        return tuple(cursor)

    def get_content_unit_keys(self, content_type, unit_ids):
        """
        """
        collection = _get_type_collection(content_type)
        # do the content_unit_keys_dict correspond to the unique indexes?
        return []

    def get_content_unit_ids(self, content_type, unit_keys):
        """
        """
        collection = _get_type_collection(content_type)
        # do the content_unit_keys_dict correspond to the unique indexes?
        return []

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
        # XXX we should store the TypeDefinitions in their own collection in
        # the db so that we can validate the metadata delta
        collection = _get_type_collection(content_type)
        content_unit = collection.find_one({'_id': unit_id})
        if content_unit is None:
            raise ContentUnitNotFound()
        content_unit = dict(content_unit)
        content_unit.update(unit_metadata_delta)
        collection.save(content_unit)

    def remove_content_unit(self, content_type, unit_id):
        """
        """
        collection = _get_type_collection(content_type)
        collection.remove({'_id': unit_id})

# utility methods --------------------------------------------------------------

def _get_type_collection(type_id):
    """
    """
    collection = content_types_db.type_units_collection(type_id)
    return collection
