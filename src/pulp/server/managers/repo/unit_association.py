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

from pulp.server.db.model.gc_repository import RepoContentUnit
import pulp.server.managers.factory as manager_factory

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

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param unit_type_id: identifies the type of unit being added
        @type  unit_type_id: str

        @param unit_id: uniquely identifies the unit within the given type
        @type  unit_id: str
        """

        # If the association already exists, no need to do anything else
        existing_association = RepoContentUnit.get_collection().find_one({'repo_id' : repo_id, 'unit_id' : unit_id, 'unit_type_id' : unit_type_id})
        if existing_association is not None:
            return

        # Create the database entry
        association = RepoContentUnit(repo_id, unit_id, unit_type_id)
        RepoContentUnit.get_collection().save(association, safe=True)

    def associate_all_by_ids(self, repo_id, unit_type_id, unit_id_list):
        """
        Creates multiple associations between the given repo and content units.

        See associate_unit_by_id for semantics.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param unit_type_id: identifies the type of unit being added
        @type  unit_type_id: str

        @param unit_id_list: list of unique identifiers for units within the given type
        @type  unit_id_list: list of str
        """

        # There may be a way to batch this in mongo which would be ideal for a
        # bulk operation like this. But for deadline purposes, this call will
        # simply loop and call the single method.

        for unit_id in unit_id_list:
            self.associate_unit_by_id(repo_id, unit_type_id, unit_id)

    def unassociate_unit_by_id(self, repo_id, unit_type_id, unit_id):
        """
        Removes the association between a repo and the given unit.

        If no association exists between the repo and unit, this call has no
        effect.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param unit_type_id: identifies the type of unit being removed
        @type  unit_type_id: str

        @param unit_id: uniquely identifies the unit within the given type
        @type  unit_id: str
        """
        unit_coll = RepoContentUnit.get_collection()
        unit_coll.remove({'repo_id' : repo_id, 'unit_id' : unit_id, 'unit_type_id' : unit_type_id}, safe=True)

    def unassociate_all_by_ids(self, repo_id, unit_type_id, unit_id_list):
        """
        Removes the association between a repo and a number of units.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param unit_type_id: identifies the type of units being removed
        @type  unit_type_id: str

        @param unit_id_list: list of unique identifiers for units within the given type
        @type  unit_id_list: list of str
        """
        unit_coll = RepoContentUnit.get_collection()
        unit_coll.remove({'repo_id' : repo_id, 'unit_type_id' : unit_type_id, 'unit_id' : {'$in' : unit_id_list}}, safe=True)

    # -- association queries --------------------------------------------------

    def get_unit_ids(self, repo_id, unit_type_id=None):
        """
        Get the ids of the content units associated with the repo.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param unit_type_id: optional; if specified only unit ids of the
                             specified type are returned

        @return: dict of unit type id: list of content unit ids
        @rtype:  dict of str: list of str
        """
        unit_ids = {}
        collection = RepoContentUnit.get_collection()
        spec_doc = {'repo_id': repo_id}
        if unit_type_id is not None:
            spec_doc['unit_type_id'] = unit_type_id
        cursor = collection.find(spec_doc)
        for content_unit in cursor:
            ids = unit_ids.setdefault(content_unit['unit_type_id'], [])
            ids.append(content_unit['unit_id'])
        return unit_ids

    def get_units(self, repo_id):
        """
        Returns all content units associated with the given repository.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @return: dict of type ID to list of unit dicts
        @rtype:  dict of {str : [dict]}
        """

        result = {}

        # First step is to retrieve all the IDs from the mapping collection
        all_units = list(RepoContentUnit.get_collection().find({'repo_id': repo_id}))
        for unit in all_units:
            type_id = unit['unit_type_id']
            unit_list = result.get(type_id, [])
            unit_list.append(unit['unit_id'])
            result[type_id] = unit_list

        # Now we can batch up the actual unit retrievals by type rather than
        # hammer the database asking for each unit individually
        content_query_manager = manager_factory.content_query_manager()
        for type_id, unit_id_list in result.items():
            unit_list = content_query_manager.get_multiple_units_by_ids(type_id, unit_id_list)
            result[type_id] = unit_list

        return result