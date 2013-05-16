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
    def _import_manifest(manifest):
        units = {}
        index = 0
        for unit in manifest.get_units():
            key = UniqueKey(unit)
            units[key] = index
            index += 1
        return units

    @staticmethod
    def _import_units_on_child(unit_iterator):
        units = {}
        for unit in unit_iterator:
            del unit['metadata']
            key = UniqueKey(unit)
            units[key] = unit
        return units

    def __init__(self, manifest, unit_iterator):
        """
        :param manifest: The manifest containing the units associated
            with a specific repository.
        :type manifest: pulp_node.manifest.Manifest
        :param unit_iterator: An iterator of the units associated
            with a specific repository.
        :type unit_iterator: iterable
        """
        self.manifest = manifest
        self.units_on_parent = self._import_manifest(manifest)
        self.units_on_child = self._import_units_on_child(unit_iterator)

    def units_on_parent_only(self):
        """
        Listing of units contained in the parent inventory
        but not contained in the child inventory.
        :return: Iterator of units that need to be added.
        :rtype: generator
        """
        indexes = [i for k, i in self.units_on_parent.items() if k not in self.units_on_child]
        return self.manifest.get_units(indexes)

    def units_on_child_only(self):
        """
        Listing of units contained in the child inventory
        but not contained in the parent inventory.
        :return: List of units that need to be purged.
        :rtype: list
        """
        return [u for k, u in self.units_on_child.items() if k not in self.units_on_parent]