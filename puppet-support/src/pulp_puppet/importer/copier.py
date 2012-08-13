# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from pulp_puppet.common import constants

from pulp.plugins.conduits.mixins import UnitAssociationCriteria

def copy_units(import_conduit, units):
    """
    Copies puppet modules from one repo into another. There is nothing that
    the importer needs to do; it maintains no state in the working directory
    so the process is to simply tell Pulp to import each unit specified.
    """

    # Determine which units are being copied
    if units is None:
        criteria = UnitAssociationCriteria(type_ids=[constants.TYPE_PUPPET_MODULE])
        units = import_conduit.get_source_units(criteria=criteria)

    # Associate to the new repository
    for u in units:
        import_conduit.associate_unit(u)
