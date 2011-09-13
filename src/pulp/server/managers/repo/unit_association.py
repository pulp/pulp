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

"""
Contains the manager class and exceptions for handling the mappings between
repositories and content units.
"""

import logging

from pulp.server.db.model.gc_repository import Repo, RepoContentUnit

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- manager ------------------------------------------------------------------

class RepoUnitAssociationManager:
    """
    Manager used to handle the associations between repositories and content
    units. The functionality provided within assumes the repo and units have
    been created outside of this manager.
    """

    # -- association manipulation ---------------------------------------------

    def associate_unit_by_id(self, repo_id, unit_type_id, unit_id):
        """
        Creates an association between the given repository and content unit.

        If there is already an association between the given repo and content
        unit, this call has no effect.

        Both repo and unit must exist in the database prior to this call,
        however this call will not verify that for performance reasons. Care
        should be taken by the caller to preserve the data integrity.
        """

        # If the association already exists, no need to do anything else
        existing_association = RepoContentUnit.get_collection().find_one({'repo_id' : repo_id, 'unit_id' : unit_id, 'unit_type_id' : unit_type_id})
        if existing_association is not None:
            return

        # Create the database entry
        association = RepoContentUnit(repo_id, unit_id, unit_type_id)
        RepoContentUnit.get_collection().save(association)

    def unassociate_unit_by_id(self, repo_id, unit_type_id, unit_id):
        """
        Removes the association between a repo and the given unit.

        If no association exists between the repo and unit, this call has no
        effect.
        """
        RepoContentUnit.get_collection().remove({'repo_id' : repo_id, 'unit_id' : unit_id, 'unit_type_id' : unit_type_id})
