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

    def associate_unit_by_key(self, repo_id, unit_type_id, unit_key):
        """
        Creates an association between the given repository and a content unit
        with the given key and type. This call takes the extra step of looking
        up the unit's ID based on the provided key.

        If there is already an association between the given repo and content
        unit, this call has no effect.

        Both repo and unit must exist in the database prior to this call,
        however this call will not verify that for performance reasons. Care
        should be taken by the caller to preserve the data integrity.
        """

        # TODO: call to content manager to get ID by key
        unit_id = ''

        self.associate_unit_by_id(repo_id, unit_type_id, unit_id)

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

    def unassociate_unit_by_key(self, repo_id, unit_type_id, unit_key):
        """
        Removes the association between a repo and the unit identified by the
        given unit key. This call takes the extra step of looking up the unit's
        ID based on the provided key.

        If no association exists between the repo and unit, this call has no
        effect.
        """

        # TODO: call to content manager to get ID by key
        unit_id = ''

        self.unassociate_unit_by_id(repo_id, unit_type_id, unit_id)

    def unassociate_unit_by_id(self, repo_id, unit_type_id, unit_id):
        """
        Removes the association between a repo and the given unit.

        If no association exists between the repo and unit, this call has no
        effect.
        """
        RepoContentUnit.get_collection().remove({'repo_id' : repo_id, 'unit_id' : unit_id, 'unit_type_id' : unit_type_id})

    # -- association queries --------------------------------------------------

    def unit_associations_for_repo(self, repo_id):
        """
        Returns all unit associations for the given repo. The full association
        linking object will be returned for each unit.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @return: list of DB objects describing all of the units associated units
                 to the repo; empty list if there are no associations
        @rtype:  list of dict
        """

        # This call isn't meant to be a public facing call, so there is no
        # translation between database object and public object model.

        results = list(RepoContentUnit.get_collection().find({'repo_id' : repo_id}))
        return results

    def unit_keys_for_repo(self, repo_id):
        """
        Returns a list of all unit keys for units associated with the given repo.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @return: list of unit keys for all associated units; empty list if there
                 are no associations
        @rtype:  list of dict
        """
        pass