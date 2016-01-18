from pulp.plugins.types.database import type_units_collection
from pulp.plugins.util.misc import paginate
from pulp.server.controllers.units import get_unit_key_fields_for_type
from pulp.server.db.model.repository import RepoContentUnit
from pulp.server.config import config as pulp_conf


class NodesConduit(object):

    @staticmethod
    def get_units(repo_id):
        """
        Get all units associated with a repository.
        :param repo_id: The repository ID used to query the units.
        :type repo_id: str
        :return: unit iterator
        :rtype: UnitsIterator
        """
        unit_ids = {}
        associations = {}
        collection = RepoContentUnit.get_collection()
        for association in collection.find({'repo_id': repo_id}):
            unit_id = association['unit_id']
            type_id = association['unit_type_id']
            associations[unit_id] = association
            id_list = unit_ids.setdefault(type_id, [])
            id_list.append(unit_id)
        return UnitsIterator(associations, unit_ids)


class UnitsIterator(object):
    """
    Provides a memory efficient iterator of associated content units.
    """

    @staticmethod
    def associated_unit(association, unit):
        """
        Create a dictionary that is a composite of a unit association and the unit.

        :param association: A unit association DB record.
        :type association: dict
        :param unit: A DB unit record.
        :type unit: dict
        :return: A composite of the unit association and the unit.
        :rtype: dict
        """
        unit_key = {}
        unit_id = unit.pop('_id')
        type_id = association['unit_type_id']
        for key in get_unit_key_fields_for_type(type_id):
            unit_key[key] = unit.pop(key, None)
        storage_dir = pulp_conf.get('server', 'storage_dir')
        storage_path = unit.pop('_storage_path', None)
        last_updated = unit.pop('_last_updated', 0.0)
        if storage_path:
            relative_path = storage_path[len(storage_dir):].lstrip('/')
        else:
            relative_path = None
        return dict(
            unit_id=unit_id,
            type_id=type_id,
            unit_key=unit_key,
            storage_path=storage_path,
            relative_path=relative_path,
            last_updated=last_updated,
            metadata=unit)

    @staticmethod
    def open_cursors(unit_ids):
        """
        Get a generator of unit cursors.

        :param unit_ids: A dictionary of unit_ids keyed by type_id.
        :type unit_ids: dict
        :return: A list of open cursors.
        :rtype: generator
        """
        for type_id, id_list in unit_ids.items():
            for page in paginate(id_list):
                query = {'_id': {'$in': page}}
                collection = type_units_collection(type_id)
                cursor = collection.find(query)
                yield cursor

    def get_units(self, associations, unit_ids):
        """
        Get units generator.

        :param associations: A dictionary of unit associates keyed by type_id.
        :type associations: dict
        :param unit_ids: A dictionary of unit_ids keyed by type_id.
        :type unit_ids: dict
        :return: A composite association and unit.
        :rtype: generator
        """
        for cursor in UnitsIterator.open_cursors(unit_ids):
            for unit in cursor:
                unit_id = unit['_id']
                association = associations[unit_id]
                yield self.associated_unit(association, unit)

    def __init__(self, associations, unit_ids):
        """
        :param associations: A dictionary of unit associates keyed by type_id.
        :type associations: dict
        :param unit_ids: A dictionary of unit_ids keyed by type_id.
        :type unit_ids: dict
        """
        self.length = len(associations)
        self.unit_generator = self.get_units(associations, unit_ids)

    def next(self):
        return self.unit_generator.next()

    def __iter__(self):
        return self

    def __len__(self):
        return self.length
