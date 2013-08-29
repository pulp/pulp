# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp.plugins.types import database as types_db
from pulp.server.db.model.repository import RepoContentUnit
from pulp.server.config import config as pulp_conf


# --- nodes conduit  ----------------------------------------------------------


class NodesConduit(object):

    def get_units(self, repo_id):
        """
        Get all units associated with a repository.
        :param repo_id: The repository ID used to query the units.
        :type repo_id: str
        :return: unit iterator
        :rtype: UnitsIterator
        """
        units = {}
        types = {}
        collection = RepoContentUnit.get_collection()
        for unit in collection.find({'repo_id': repo_id}):
            unit_id = unit['unit_id']
            type_id = unit['unit_type_id']
            units[unit_id] = unit
            unit_list = types.setdefault(type_id, [])
            unit_list.append(unit['unit_id'])
        return UnitsIterator(units, types)


# --- typedef -----------------------------------------------------------------


class Typedef(object):

    def __init__(self):
        self.cached = {}

    def get(self, type_id):
        typedef = self.cached.get(type_id)
        if typedef is None:
            typedef = types_db.type_definition(type_id)
            self.cached[type_id] = typedef
        return typedef


# --- iterators ---------------------------------------------------------------


class UnitsIterator:

    @staticmethod
    def associated_unit(typedef, unit, metadata):
        unit_key = {}
        for key in typedef['unit_key']:
            unit_key[key] = metadata.pop(key, None)
        metadata.pop('_id', None)
        storage_dir = pulp_conf.get('server', 'storage_dir')
        storage_path = metadata.pop('_storage_path', None)
        last_updated = metadata.pop('_last_updated', 0.0)
        if storage_path:
            relative_path = storage_path[len(storage_dir):].lstrip('/')
        else:
            relative_path = None
        return dict(
            unit_id=unit['unit_id'],
            type_id=unit['unit_type_id'],
            unit_key=unit_key,
            storage_path=storage_path,
            relative_path=relative_path,
            last_updated=last_updated,
            owner_type=unit.get('owner_type'),
            owner_id=unit.get('owner_id'),
            metadata=metadata)

    @staticmethod
    def open_cursors(types):
        for type_id, unit_ids in types.items():
            query = {'_id': {'$in': unit_ids}}
            collection = types_db.type_units_collection(type_id)
            cursor = collection.find(query)
            yield cursor

    @staticmethod
    def get_units(units, types):
        typedefs = Typedef()
        for cursor in UnitsIterator.open_cursors(types):
            for metadata in cursor:
                unit_id = metadata['_id']
                unit = units[unit_id]
                type_id = unit['unit_type_id']
                typedef = typedefs.get(type_id)
                yield UnitsIterator.associated_unit(typedef, unit, metadata)

    def __init__(self, units, types):
        self.length = len(units)
        self.unit_generator = UnitsIterator.get_units(units, types)

    def next(self):
        return self.unit_generator.next()

    def __iter__(self):
        return self

    def __len__(self):
        return self.length