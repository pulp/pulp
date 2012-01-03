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

import copy
import logging
import pymongo

import pulp.server.content.types.database as types_db
import pulp.server.content.loader as plugin_loader
from pulp.server.db.model.gc_repository import RepoContentUnit
import pulp.server.managers.factory as manager_factory
from pulp.server.managers.repo._exceptions import InvalidOwnerType, MissingRepo

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# Shadowed here to remove the need for the caller to import RepoContentUnit
# to get access to them
OWNER_TYPE_IMPORTER = RepoContentUnit.OWNER_TYPE_IMPORTER
OWNER_TYPE_USER = RepoContentUnit.OWNER_TYPE_USER

_OWNER_TYPES = (OWNER_TYPE_IMPORTER, OWNER_TYPE_USER)

# Valid sort strings
SORT_TYPE_ID = 'type_id'
SORT_OWNER_TYPE = 'owner_type'
SORT_OWNER_ID = 'owner_id'
SORT_CREATED = 'created'
SORT_UPDATED = 'updated'

_VALID_SORTS = (SORT_TYPE_ID, SORT_OWNER_TYPE, SORT_OWNER_ID, SORT_CREATED, SORT_UPDATED)

SORT_ASCENDING = pymongo.ASCENDING
SORT_DESCENDING = pymongo.DESCENDING

_VALID_DIRECTIONS = (SORT_ASCENDING, SORT_DESCENDING)

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

        if owner_type not in _OWNER_TYPES:
            raise InvalidOwnerType()

        # If the association already exists, no need to do anything else
        spec = {'repo_id' : repo_id,
                'unit_id' : unit_id,
                'unit_type_id' : unit_type_id,
                'owner_type' : owner_type,
                'owner_id' : owner_id,}
        existing_association = RepoContentUnit.get_collection().find_one(spec)
        if existing_association is not None:
            return

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

    def associate_from_repo(self, source_repo_id, dest_repo_id, criteria=None):
        """
        Creates associations in a repository based on the contents of a source
        repository. Units from the source repository can be filtered by
        specifying a criteria object.

        The destination repository must have an importer that can support
        the types of units being associated. This is done by analyzing the
        unit list and the importer metadata and takes place before the
        destination repository is called.

        Pulp does not actually perform the associations as part of this call.
        The unit list is determined and passed to the destination repository's
        importer. It is the job of the importer to make the associate calls
        back into Pulp where applicable.

        @param source_repo_id: identifies the source repository
        @type  source_repo_id: str

        @param dest_repo_id: identifies the destination repository
        @type  dest_repo_id: str

        @param criteria: optional; if specified, will filter the units retrieved
                         from the source repository
        @type  criteria: L{Criteria}

        @raises MissingRepo: if either of the specified repositories don't exist
        @raises MissingImporter: if the destination repository does not have
                a configured importer
        """

        # Validation
        repo_query_manager = manager_factory.repo_query_manager()
        importer_manager = manager_factory.repo_importer_manager()

        source_repo = repo_query_manager.find_by_id(source_repo_id)
        if source_repo is None:
            raise MissingRepo(source_repo_id)

        dest_repo = repo_query_manager.find_by_id(dest_repo_id)
        if dest_repo is None:
            raise MissingRepo(dest_repo_id)

        # This will raise MissingImporter if there isn't one, which is the
        # behavior we want this method to exhibit, so just let it bubble up.
        importer = importer_manager.get_importer(dest_repo_id)

        supported_type_ids = plugin_loader.list_importer_types(importer['importer_type_id'])

        # Retrieve the units to be associated


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

        DEPRECATED: the get_units calls should be used, limiting the returned
          fields to just the IDs.

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

    def get_units_across_types(self, repo_id, criteria=None):
        """
        Retrieves data describing units associated with the given repository
        along with information on the association itself.

        As this call may span multiple unit types, sort fields are
        restricted to those related to the association itself:
        - Type ID
        - First Associated
        - Last Updated
        - Owner Type
        - Owner ID

        Multiple sort fields from the above list are supported. If no sort is
        provided, units will be sorted by unit_type_id and created (in order).

        @param repo_id: identifies the repository
        @type  repo_id: str

        @param criteria: if specified will drive the query
        @type  criteria: L{Criteria}
        """

        # For simplicity, create a criteria if one is not provided and use its defaults
        if criteria is None:
            criteria = Criteria()

        # -- association collection lookup ------------------------------------

        spec = {'repo_id' : repo_id}

        # Limit to certain type IDs if specified
        if criteria.type_ids is not None:
            spec['unit_type_id'] = {'$in' : criteria.type_ids}

        # Just in case the caller stuffed this into the criteria
        association_filters = criteria.association_filters
        association_filters.pop('repo_id', None)
        association_filters.pop('unit_type_id', None)

        # Merge in the association filters
        spec.update(association_filters)

        cursor = RepoContentUnit.get_collection().find(spec, fields=criteria.association_fields)

        # Add the sort clauses if specified; sort can take either a string
        # or list so just pass in the sort directly. Mongo will ignore
        # multiple calls to sort and only use the last one called, so only a
        # single call is required here.
        if criteria.association_sort is not None:
            cursor.sort(criteria.association_sort)
        else:
            # If an explicit sort is not provided, default to one for consistency
            cursor.sort([('unit_type_id', SORT_ASCENDING), ('created', SORT_ASCENDING)])

        # Apply the limit and skip here since no sorting is done in the unit
        # lookup phase.
        if criteria.limit is not None:
            cursor.limit(criteria.limit)

        if criteria.skip is not None:
            cursor.skip(criteria.skip)

        # Finally do the query and assemble the associations structure
        units = list(cursor)

        # -- remove multiple associations -------------------------------------

        if criteria.remove_duplicates:
            units = self._remove_duplicate_associations(units)

        # -- unit lookups -----------------------------------------------------

        # By this point, we've applied all of the filters, sorting, and limits.
        # We simply need to look up the unit metadata itself and merge it into the
        # combined association and unit metadata dictionary.

        for u in units:
            type_collection = types_db.type_units_collection(u['unit_type_id'])
            metadata = type_collection.find_one({'_id' : u['unit_id']})
            u['metadata'] = metadata

        return units

    def get_units_by_type(self, repo_id, type_id, criteria=None):
        """
        Retrieves data describing units of the given type associated with the
        given repository. Information on the associations themselves is also
        provided.

        The sort fields may be from either the association data OR the
        unit fields. A mix of both is not supported. Multiple sort fields
        are supported as long as they come from the same area.

        If a sort is not provided, the units will be sorted ascending by each
        value in the unit key for the given type.

        @param repo_id: identifies the repository
        @type  repo_id: str

        @param type_id: limits returned units to the given type
        @type  type_id: str

        @param criteria: if specified will drive the query
        @type  criteria: L{Criteria}
        """

        # For simplicity, create a criteria if one is not provided and use its defaults
        if criteria is None:
            criteria = Criteria()

        # -- association collection lookup ------------------------------------

        spec = {'repo_id' : repo_id,
                'unit_type_id' : type_id}

        # Stip out the type ID and repo fields if they were accidentally specified in the criteria
        association_spec = criteria.association_filters
        association_spec.pop('unit_type_id', None)
        association_spec.pop('repo_id', None)

        # Merge in the given association filters
        spec.update(association_spec)

        cursor = RepoContentUnit.get_collection().find(spec, fields=criteria.association_fields)

        # If the sort clause applies to the association metadata, we
        # apply the limit and skips here as well. If the sort is not
        # provided, it will be defaulted at the unit type level.

        association_sorted = False # flag so we can know this later

        association_sort = criteria.association_sort
        if association_sort is not None:
            association_sorted = True

            cursor.sort(association_sort)

            if criteria.limit is not None:
                cursor.limit(criteria.limit)

            if criteria.skip is not None:
                cursor.skip(criteria.skip)

        unit_associations = list(cursor)

        # -- remove multiple associations -------------------------------------

        if criteria.remove_duplicates:
            unit_associations = self._remove_duplicate_associations(unit_associations)

        # -- unit lookups -----------------------------------------------------

        # If the sorting was not done on association fields, we do it here. If
        # specified, we can use those fields. If not, we default to the unit key.

        type_collection = types_db.type_units_collection(type_id)
        unit_spec = criteria.unit_filters

        # Depending on where the sort occurs, the algorithm proceeds in
        # drastically different ways. Both of these absolutely must be stress
        # tested individually and we need to make sure QE knows the role of
        # the sort in determining which code branch is followed.

        if association_sorted:
            # The units are already sorted, so we have to maintain the order in
            # the units list.

            for u in unit_associations:
                spec = copy.copy(unit_spec)
                spec['_id'] = u['unit_id']
                metadata = type_collection.find_one(spec, fields=criteria.unit_fields)
                u['metadata'] = metadata

            return unit_associations

        else:
            # Sorting will be done in the units collection. Since the type is
            # consistent, we can rely on the unit's _id for uniqueness. That
            # means we can transform the associations into a simple dict lookup
            # by _id when we need to merge in the association data.

            # Restructure the associations by ID so we can look them up later and
            # so we have a list of all unit IDs to pass as a filter.
            associations_by_id = dict([(u['unit_id'], u) for u in unit_associations])

            # We only want to return units with an association, so add in all of
            # the unit IDs we found earlier.
            unit_spec['_id'] = {'$in' : associations_by_id.keys()}

            cursor = type_collection.find(unit_spec, fields=criteria.unit_fields)

            # Determine what our sort criteria will look like
            if criteria.unit_sort is None:
                # Default the sort to the unit key
                unit_key_fields = types_db.type_units_unit_key(type_id)
                sort_spec = [(u, SORT_ASCENDING) for u in unit_key_fields]
                cursor.sort(sort_spec)
            else:
                cursor.sort(criteria.unit_sort)

            # Since the sorting is done here, this is the only place we can
            # apply the limit/skip.
            if criteria.limit is not None:
                cursor.limit(criteria.limit)

            if criteria.skip is not None:
                cursor.skip(criteria.skip)

            # This will load all of the units and they will be filtered,
            # limited, and sorted.
            units = list(cursor)

            # Now we just need to merge in the association data
            merged_units = []
            for u in units:
                association = associations_by_id[u['_id']]
                association['metadata'] = u
                merged_units.append(association)

            return merged_units

    def _remove_duplicate_associations(self, units):
        """
        For units that are associated with a repository more than once, this
        method will strip out all duplicate associations, only returning the
        association with the earliest created date.

        @param units: list of unit dicts retrieved from the database
        @type  units: list of dict

        @return: new list of units (the parameter list will not be affected);
                 len(returned_units) <= len(units)
        @rtype:  list
        """

        # Used to hold on to the earliest created association for comparison
        uuid_to_associations = {}

        # Flag for each unit in units; if False it will not be included in the returned list
        keep_units = [True for i in range(len(units))]

        def _unit_uuid(unit_association):
            return unit_association['unit_type_id'] + '+' + unit_association['unit_id']

        for i in range(0, len(units)):
            unit_uuid = _unit_uuid(units[i])

            if unit_uuid not in uuid_to_associations:
                # First association for the unit, store its index and unit and move on
                uuid_to_associations[unit_uuid] = (i, units[i])
            else:
                # Determine which should be removed, the previously found one or this one
                previous_tuple = uuid_to_associations[unit_uuid]
                if previous_tuple[1]['created'] < units[i]['created']:
                    keep_units[i] = False
                else:
                    keep_units[previous_tuple[0]] = False
                    uuid_to_associations[unit_uuid] = (i, units[i])


        # Use the keep_units flags to strip out the duplicates (this is
        # cheaper than keeping track of which to remove and updating the
        # existing list).
        clean_units = [u for b, u in zip(keep_units, units) if b]
        return clean_units

# -- association criteria -----------------------------------------------------

class Criteria:

    # Shadowed here for convenience
    SORT_ASCENDING = pymongo.ASCENDING
    SORT_DESCENDING = pymongo.DESCENDING

    def __init__(self, type_ids=None, association_filters=None, unit_filters=None,
                 association_sort=None, unit_sort=None, limit=None, skip=None,
                 association_fields=None, unit_fields=None, remove_duplicates=None):
        """
        There are a number of entry points into creating one of these instances:
        multiple REST interfaces, the plugins, etc. As such, this constructor
        does quite a bit of validation on the parameter values.

        @param type_ids: list of types to search
        @type  type_ids: [str]

        @param association_filters: mongo spec describing search parameters on
               association metadata
        @type  association_filters: dict

        @param unit_filters: mongo spec describing search parameters on unit
               metadata; only used when a single type ID is specified
        @type  unit_filters: dict

        @param association_sort: ordered list of fields and directions; may only
               contain association metadata
        @type  association_sort: [(str, <SORT_* constant>)]

        @param unit_sort: ordered list of fields and directions; only used when
               a single type ID is specified
        @type  unit_sort: [(str, <SORT_* constant>)]

        @param limit: maximum number of results to return
        @type  limit: int

        @param skip: number of results to skip
        @type  skip: int

        @param association_fields: if specified, only the given fields from the
               association's metadata will be included in returned units
        @type  association_fields: list of str

        @param unit_fields: if specified, only the given fields from the unit's
               metadata are returned; only applies when a single type ID is
               specified
        @type  unit_fields: list of str

        @param remove_duplicates: if True, units with multiple associations will
               only return a single association; defaults to False
        @type  remove_duplicates: bool
        """

        # A default instance will be used in the case where no criteria is
        # passed in, so use sane defaults here.

        if type_ids is not None and  not isinstance(type_ids, (list, tuple)):
            type_ids = [type_ids]
        self.type_ids = type_ids

        self.association_filters = association_filters or {}
        self.unit_filters = unit_filters or {}

        self.association_sort = association_sort
        self.unit_sort = unit_sort

        self.limit = limit
        self.skip = skip

        # The unit_id and unit_type_id are required as association returned data;
        # frankly it doesn't make sense without them but it's also a technical
        # requirement for the algorithm to run. Make sure they are there.
        if association_fields is not None:
            if 'unit_id' not in association_fields: association_fields.append('unit_id')
            if 'unit_type_id' not in association_fields: association_fields.append('unit_type_id')

        self.association_fields = association_fields
        self.unit_fields = unit_fields

        if remove_duplicates is None:
            remove_duplicates = False
        self.remove_duplicates = remove_duplicates

    def __str__(self):
        s = ''
        if self.type_ids: s += 'Type IDs [%s] ' % self.type_ids
        if self.association_filters: s += 'Assoc Filters [%s] ' % self.association_filters
        if self.unit_filters is not None: s += 'Unit Filters [%s] ' % self.unit_filters
        if self.association_sort is not None: s += 'Assoc Sort [%s] ' % self.association_sort
        if self.unit_sort is not None: s += 'Unit Sort [%s] ' % self.unit_sort
        if self.limit: s += 'Limit [%s] ' % self.limit
        if self.skip: s += 'Skip [%s] ' % self.skip
        if self.association_fields: s += 'Assoc Fields [%s] ' % self.association_fields
        if self.unit_fields: s += 'Unit Fields [%s] ' % self.unit_fields
        s += 'Remove Duplicates [%s]' % self.remove_duplicates
        return s
