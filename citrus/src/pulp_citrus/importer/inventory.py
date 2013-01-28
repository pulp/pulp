# Copyright (c) 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


def unit_dictionary(units):
    """
    Build a dictionary of units keyed by UnitKey using
    the specified list of units.
    :param units: A list of content units.
        Each unit is either: (Unit|dict)
    :type units: list
    :return: A dictionary of units keyed by UnitKey.
    :rtype: dict
    """
    items = [(UnitKey(u), u) for u in units]
    return dict(items)


class UnitKey:
    """
    A unique unit key consisting of a unit's type_id & unit_key.
    The unit key is sorted to ensure consistency.
    :ivar uid: The unique ID.
    :type uid: A tuple of: (type_id, unit_key)
    """

    def __init__(self, unit):
        """
        :param unit: A content unit.
        :type unit: (dict|Unit)
        """
        if isinstance(unit, dict):
            type_id = unit['type_id']
            unit_key = tuple(sorted(unit['unit_key'].items()))
        else:
            type_id = unit.type_id
            unit_key = tuple(sorted(unit.unit_key.items()))
        self.uid = (type_id, unit_key)

    def __hash__(self):
        return hash(self.uid)

    def __eq__(self, other):
        return self.uid == other.uid

    def __ne__(self, other):
        return self.uid != other.uid


class UnitInventory:
    """
    The unit inventory contains both the upstream and local inventory
    of content units associated with a specific repository.  Each is contained
    within a dictionary keyed by {UnitKey} to ensure uniqueness.
    :ivar local: The local inventory.
    :type local: dict
    :ivar upstream: The upstream inventory.
    :type upstream: dict
    """

    def __init__(self, local, upstream):
        """
        :param local: The local inventory.
        :type local: dict
        :param upstream: The upstream inventory.
        :type upstream: dict
        """
        self.local = local
        self.upstream = upstream

    def upstream_only(self):
        """
        Listing of units contained in the upstream inventory
        but not contained in the local inventory.
        :return: List of units that need to be added.
        :rtype: list
        """
        units = []
        for k, unit in self.upstream.items():
            if k not in self.local:
                units.append(unit)
        return units

    def local_only(self):
        """
        Listing of units contained in the local inventory
        but not contained in the upstream inventory.
        :return: List of units that need to be purged.
        :rtype: list
        """
        units = []
        for k, unit in self.local.items():
            if k not in self.upstream:
                units.append(units)
        return units