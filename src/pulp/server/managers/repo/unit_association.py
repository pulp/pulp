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
from pulp.server.managers.repo._exceptions import InvalidOwnerType

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# Shadowed here to remove the need for the caller to import RepoContentUnit
# to get access to them
OWNER_TYPE_IMPORTER = RepoContentUnit.OWNER_TYPE_IMPORTER
OWNER_TYPE_USER = RepoContentUnit.OWNER_TYPE_USER

_OWNER_TYPES = (OWNER_TYPE_IMPORTER, OWNER_TYPE_USER)

# -- manager ------------------------------------------------------------------

class RepoUnitAssociationManager:
    """
    Manager used to handle the associations between repositories and content
    units. The functionality provided within assumes the repo and units have
    been created outside of this manager.
    """

    # -- association manipulation ---------------------------------------------

    def associate_unit_by_id(self, repo_id, unit_type_id, unit_id, owner_type, owner_id):
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

        @param owner_type: category of the caller making the association;
                           must be one of the OWNER_* variables in this module
        @type  owner_type: str

        @param owner_id: identifies the caller making the association, either
                         the importer ID or user login
        @type  owner_id: str

        @raises InvalidOwnerType: if the given owner type is not of the valid enumeration
        """

        # If the association already exists, no need to do anything else
        existing_association = RepoContentUnit.get_collection().find_one({'repo_id' : repo_id, 'unit_id' : unit_id, 'unit_type_id' : unit_type_id})
        if existing_association is not None:
            return

        if owner_type not in _OWNER_TYPES:
            raise InvalidOwnerType()

        # Create the database entry
        association = RepoContentUnit(repo_id, unit_id, unit_type_id, owner_type, owner_id)
        RepoContentUnit.get_collection().save(association, safe=True)

    def associate_all_by_ids(self, repo_id, unit_type_id, unit_id_list, owner_type, owner_id):
        """
        Creates multiple associations between the given repo and content units.

        See associate_unit_by_id for semantics.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param unit_type_id: identifies the type of unit being added
        @type  unit_type_id: str

        @param unit_id_list: list of unique identifiers for units within the given type
        @type  unit_id_list: list of str

        @param owner_type: category of the caller making the association;
                           must be one of the OWNER_* variables in this module
        @type  owner_type: str

        @param owner_id: identifies the caller making the association, either
                         the importer ID or user login
        @type  owner_id: str

        @raises InvalidOwnerType: if the given owner type is not of the valid enumeration
        """

        # There may be a way to batch this in mongo which would be ideal for a
        # bulk operation like this. But for deadline purposes, this call will
        # simply loop and call the single method.

        for unit_id in unit_id_list:
            self.associate_unit_by_id(repo_id, unit_type_id, unit_id, owner_type, owner_id)

    def unassociate_unit_by_id(self, repo_id, unit_type_id, unit_id, owner_type, owner_id):
        """
        Removes the association between a repo and the given unit. Only the
        association made by the given owner will be removed. It is possible the
        repo will still have a manually created association will for the unit.

        If no association exists between the repo and unit, this call has no
        effect.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param unit_type_id: identifies the type of unit being removed
        @type  unit_type_id: str

        @param unit_id: uniquely identifies the unit within the given type
        @type  unit_id: str

        @param owner_type: category of the caller who created the association;
                           must be one of the OWNER_* variables in this module
        @type  owner_type: str

        @param owner_id: identifies the caller who created the association, either
                         the importer ID or user login
        @type  owner_id: str
        """
        spec = {'repo_id' : repo_id,
                'unit_id' : unit_id,
                'unit_type_id' : unit_type_id,
                'owner_type' : owner_type,
                'owner_id' : owner_id,
                }

        unit_coll = RepoContentUnit.get_collection()
        unit_coll.remove(spec, safe=True)

    def unassociate_all_by_ids(self, repo_id, unit_type_id, unit_id_list, owner_type, owner_id):
        """
        Removes the association between a repo and a number of units. Only the
        association made by the given owner will be removed. It is possible the
        repo will still have a manually created association will for the unit.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param unit_type_id: identifies the type of units being removed
        @type  unit_type_id: str

        @param unit_id_list: list of unique identifiers for units within the given type
        @type  unit_id_list: list of str

        @param owner_type: category of the caller who created the association;
                           must be one of the OWNER_* variables in this module
        @type  owner_type: str

        @param owner_id: identifies the caller who created the association, either
                         the importer ID or user login
        @type  owner_id: str
        """
        spec = {'repo_id' : repo_id,
                'unit_type_id' : unit_type_id,
                'unit_id' : {'$in' : unit_id_list},
                'owner_type' : owner_type,
                'owner_id' : owner_id,
                }

        unit_coll = RepoContentUnit.get_collection()
        unit_coll.remove(spec, safe=True)

    # -- association queries --------------------------------------------------

    def get_unit_ids(self, repo_id, unit_type_id=None):
        """
        Get the ids of the content units associated with the repo. If more
        than one association exists between a unit and the repository, the
        unit ID will only be listed once.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param unit_type_id: optional; if specified only unit ids of the
                             specified type are returned

        @return: dict of unit type id: list of content unit ids
        @rtype:  dict of str: list of str
        """
        unit_ids = {}
        collection = RepoContentUnit.get_collection()

        # This used to be one query and splitting out the results by unit
        # type in memory. The problem is that we need to add in the distinct
        # clause to eliminate the potential of multiple associations to the
        # same unit. I don't think distinct will operate on two keys. I don't
        # anticipate there will be a tremendous amount of unit types passed in
        # so I'm not too worried about making one call per unit type.
        # jdob - Dec 9, 2011

        if unit_type_id is None:
            unit_type_ids = []

            # Get a list of all unit types that have at least one unit associated.
            cursor = collection.find(spec={'repo_id' : repo_id}, fields=['unit_type_id'])
            for t in cursor.distinct('unit_type_id'):
                unit_type_ids.append(t)
        else:
            unit_type_ids = [unit_type_id]

        for type_id in unit_type_ids:

            spec_doc = {'repo_id': repo_id,
                        'unit_type_id' : type_id}
            cursor = collection.find(spec_doc)

            for unit_id in cursor.distinct('unit_id'):
                ids = unit_ids.setdefault(type_id, [])
                ids.append(unit_id)

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
            unit_set = result.get(type_id, set())
            unit_set.add(unit['unit_id'])
            result[type_id] = unit_set

        # Now we can batch up the actual unit retrievals by type rather than
        # hammer the database asking for each unit individually
        content_query_manager = manager_factory.content_query_manager()
        for type_id, unit_id_list in result.items():
            unit_list = content_query_manager.get_multiple_units_by_ids(type_id, list(unit_id_list))
            result[type_id] = unit_list

        return result