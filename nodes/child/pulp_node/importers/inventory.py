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
    items = [(UniqueKey(u), u) for u in units]
    return dict(items)


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


class UnitInventory(object):
    """
    The unit inventory contains both the parent and child inventory
    of content units associated with a specific repository.  Each is contained
    within a dictionary keyed by {UnitKey} to ensure uniqueness.
    :ivar repo_id: The repository ID.
    :type repo_id: str
    :ivar child: The child inventory.
    :type child: dict
    :ivar parent: The parent inventory.
    :type parent: dict
    """

    def __init__(self, repo_id, child, parent):
        """
        :param repo_id: The repository ID.
        :type repo_id: str
        :param child: The child inventory.
        :type child: dict
        :param parent: The parent inventory.
        :type parent: dict
        """
        self.repo_id = repo_id
        self.child = child
        self.parent = parent

    def parent_only(self):
        """
        Listing of units contained in the parent inventory
        but not contained in the child inventory.
        :return: List of units that need to be added.
        :rtype: list
        """
        return [u for k, u in self.parent.items() if k not in self.child]

    def child_only(self):
        """
        Listing of units contained in the child inventory
        but not contained in the parent inventory.
        :return: List of units that need to be purged.
        :rtype: list
        """
        return [u for k, u in self.child.items() if k not in self.parent]