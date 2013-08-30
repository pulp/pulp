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

from pulp_node import constants


class UniqueKey(object):
    """
    A unique unit key consisting of a unit's type_id & unit_key.
    The unit key is sorted to ensure consistency.
    :ivar uid: The unique ID.
    :type uid: A tuple of: (type_id, unit_key)
    """

    def __init__(self, unit):
        """
        :param unit: A content unit.
        :type unit: dict
        """
        type_id = unit['type_id']
        unit_key = tuple(sorted(unit['unit_key'].items()))
        self.uid = (type_id, unit_key)

    def __hash__(self):
        return hash(self.uid)

    def __eq__(self, other):
        return self.uid == other.uid

    def __ne__(self, other):
        return self.uid != other.uid


class UnitInventory(object):
    """
    The unit inventory contains both the parent and child inventory
    of content units associated with a specific repository.  Each is contained
    within a dictionary keyed by {UnitKey} to ensure uniqueness.
    """

    @staticmethod
    def _import_parent_units(units):
        _units = {}
        for unit, ref in units:
            unit.pop('metadata', None)
            key = UniqueKey(unit)
            _units[key] = (unit, ref)
        return _units

    @staticmethod
    def _import_child_units(units):
        _units = {}
        for unit in units:
            unit.pop('metadata', None)
            key = UniqueKey(unit)
            _units[key] = unit
        return _units

    def __init__(self, base_URL, parent_units, child_units):
        """
        :param base_URL: The base URL for downloading parent units.
        :param parent_units: The content units in the parent node.
        :type parent_units: iterable
        :param child_units: The content units in the child node.
        :type child_units: iterable
        """
        self.base_URL = base_URL
        self.parent_units = self._import_parent_units(parent_units)
        self.child_units = self._import_child_units(child_units)

    def units_on_parent_only(self):
        """
        Listing of units contained in the parent inventory
        but not contained in the child inventory.
        :return: List of (unit, ref).
        :rtype: list
        """
        return [r for k, r in self.parent_units.items() if k not in self.child_units]

    def units_on_child_only(self):
        """
        Listing of units contained in the child inventory
        but not contained in the parent inventory.
        :return: List of units that need to be purged.
        :rtype: list
        """
        return [u for k, u in self.child_units.items() if k not in self.parent_units]

    def updated_units(self):
        """
        Listing of units updated on the parent.
        :return: List of (unit, ref).
        :rtype: list
        """
        updated = []
        for key, (unit, ref) in self.parent_units.items():
            child_unit = self.child_units.get(key)
            if child_unit is None:
                continue
            parent_last_updated = unit.get(constants.LAST_UPDATED, 0)
            child_last_updated = child_unit.get(constants.LAST_UPDATED, 0)
            if parent_last_updated > child_last_updated:
                updated.append((unit, ref))
        return updated