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

from pulp.plugins.model import AssociatedUnit

def to_pulp_unit(plugin_unit):
    """
    Uses the values in the plugin's unit object to create the unit metadata
    dictionary persisted by the content manager.

    @param plugin_unit: populated with values for the unit
    @type  plugin_unit: L{pulp.server.content.plugins.data.Unit}

    @return: dictionary persisted by Pulp's content manager
    @rtype:  dict
    """

    pulp_unit = dict(plugin_unit.metadata)
    pulp_unit.update(plugin_unit.unit_key)
    pulp_unit['_storage_path'] = plugin_unit.storage_path

    return pulp_unit

def to_plugin_unit(pulp_unit, type_def):
    """
    Parses the raw dictionary of content unit into the plugin's object
    representation.

    @param pulp_unit: raw dictionary of unit metadata
    @type  pulp_unit: dict

    @param type_def: Pulp stored definition for the unit type
    @type  type_def: L{pulp.server.db.model.content.ContentType}

    @return: plugin unit representation of the given unit
    @rtype:  L{pulp.server.content.plugins.data.AssociatedUnit}
    """

    # Copy so we don't mangle the original unit
    # pymongo on RHEL6 doesn't seem to like deepcopy, so do this instead
    pulp_unit = dict(pulp_unit)
    pulp_unit['metadata'] = dict(pulp_unit['metadata'])

    key_list = type_def['unit_key']

    unit_key = {}

    for k in key_list:
        unit_key[k] = pulp_unit['metadata'].pop(k)

    storage_path = pulp_unit['metadata'].pop('_storage_path', None)
    unit_id = pulp_unit.pop('unit_id', None)
    created = pulp_unit.pop('created', None)
    updated = pulp_unit.pop('updated', None)
    owner_type = pulp_unit.pop('owner_type', None)
    owner_id = pulp_unit.pop('owner_id', None)

    u = AssociatedUnit(type_def['id'], unit_key, pulp_unit['metadata'], storage_path,
                       created, updated, owner_type, owner_id)
    u.id = unit_id

    return u
