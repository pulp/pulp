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
from pulp.server.db.model.gc_repository import RepoContentUnit
from pulp.server.managers.repo._exceptions import InvalidOwnerType

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

    def get_units(self, repo_id, criteria=None):
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

        Multiple sort fields from the above list are supported.
        """

        # For simplicity, create a criteria if one is not provided and use its defaults
        if criteria is None:
            criteria = MultipleTypeCriteria()

        # -- association collection lookup ------------------------------------

        spec = {'repo_id' : repo_id}

        # Factor in all relevant search criteria if specified
        association_spec = criteria.association_spec()
        spec.update(association_spec)

        cursor = RepoContentUnit.get_collection().find(spec)

        # Add the sort clauses if specified; sort can take either a string
        # or list so just pass in the sort directly. Mongo will ignore
        # multiple calls to sort and only use the last one called, so only a
        # single call is required here.
        if criteria.sort is not None:
            cursor.sort(criteria.sort)
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

    def get_units_by_type(self, repo_id, type_id, criteria=None, fields=None):
        """
        Retrieves data describing units of the given type associated with the
        given repository. Information on the associations themselves is also
        provided.

        The sort fields may be from either the association data OR the
        unit fields. A mix of both is not supported. Multiple sort fields
        are supported as long as they come from the same area.
        """

        # For simplicity, create a criteria if one is not provided and use its defaults
        if criteria is None:
            criteria = SingleTypeCriteria()

        # -- association collection lookup ------------------------------------

        spec = {'repo_id' : repo_id,
                'unit_type_id' : type_id}
        association_spec = criteria.association_spec()
        spec.update(association_spec)

        cursor = RepoContentUnit.get_collection().find(spec)

        # If the sort clause applies to the association metadata, we
        # apply the limit and skips here as well. If the sort is not
        # provided, it will be defaulted at the unit type level.

        association_sorted = False # flag so we can know this later

        association_sort = criteria.association_sort()
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
        unit_spec = {}
        unit_spec.update(criteria.unit_spec)

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
                metadata = type_collection.find_one(spec)
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

            cursor = type_collection.find(unit_spec)

            # Determine what our sort criteria will look like
            if criteria.sort is None:
                # Default the sort to the unit key
                unit_key_field = types_db.type_units_unit_key(type_id)
                cursor.sort(unit_key_field, pymongo.ASCENDING)
            else:
                cursor.sort(criteria.sort)

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
        # The association with the earliest created date will be kept.

        # Used to hold on to the earliest created association for comparison
        uuid_to_associations = {}

        # Flag for each unit in units; if False it will not be included in the returned list
        keep_units = [True for i in range(len(units))]

        for i in range(0, len(units)):
            unit_uuid = self._unit_uuid(units[i])

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

    def _unit_uuid(self, unit_association):
        return unit_association['unit_type_id'] + '+' + unit_association['unit_id']


# -- association criteria -----------------------------------------------------

class SingleTypeCriteria:

    def __init__(self, first_associated=None, last_updated=None, owner_type=None,
                 owner_id=None, unit_fields=None,
                 limit=None, skip=None,
                 remove_duplicates=False,
                 sort=None):

        self.first_associated = first_associated
        self.last_updated = last_updated

        if owner_type is not None and owner_type not in _OWNER_TYPES:
            raise ValueError('Invalid owner type [%s]' % owner_type)

        self.owner_type = owner_type
        self.owner_id = owner_id

        if unit_fields is not None and not isinstance(unit_fields, (list, tuple)):
            unit_fields = [unit_fields]
        self.unit_fields = unit_fields

        self.limit = limit
        self.skip = skip
        self.remove_duplicates = remove_duplicates

        self.sort = sort

    def __str__(self):
        s  = 'First Associated [%s], ' % self.first_associated
        s += 'Last Updated [%s], ' % self.last_updated
        s += 'Owner Type [%s], ' % self.owner_type
        s += 'Owner ID [%s], ' % self.owner_id
        s += 'Unit Fields [%s], ' % self.unit_fields
        s += 'Limit [%s], ' % self.limit
        s += 'Skip [%s], ' % self.skip
        s += 'Sort [%s]' % self.sort
        return s

    def association_spec(self):
        spec = {}

        if self.first_associated is not None:
            spec['created'] = {self.first_associated.direction : self.first_associated.timestamp}

        if self.last_updated is not None:
            spec['updated'] = {self.last_updated.direction : self.last_updated.timestamp}

        if self.owner_type is not None:
            spec['owner_type'] = self.owner_type

        if self.owner_id is not None:
            spec['owner_id'] = self.owner_id

        return spec

    def association_sort_fields(self):
        """
        Analyzes the given sort fields to determine if the sort is
        on the association metadata or on the unit field metadata. If any
        association fields are provided, they will be returned from this call.
        This effectively strips out any unit fields specified in case the caller
        attempts to assemble a bad criteria.
        If no sort is specified or it does not contain association fields,
        None is returned.

        @return: ordered list of fields to pass to the association-level sort
                 if the criteria indicates to do so
        @rtype: list of str or None
        """

        if self.sort is None:
            return None

        association_sorts = [o for o in self.sort if o[0] in _VALID_SORTS]

        if len(association_sorts) is 0:
            return None
        else:
            return association_sorts



class MultipleTypeCriteria:

    def __init__(self, type_ids=None, first_associated=None, last_updated=None,
                 owner_type=None, owner_id=None,
                 limit=None, skip=None,
                 remove_duplicates=False,
                 sort=None):

        if type_ids is not None and not isinstance(type_ids, (list, tuple)):
            type_ids = [type_ids]
        self.type_ids = type_ids

        self.first_associated = first_associated
        self.last_updated = last_updated

        if owner_type is not None and owner_type not in _OWNER_TYPES:
            raise ValueError('Invalid owner type [%s]' % owner_type)

        self.owner_type = owner_type
        self.owner_id = owner_id

        self.limit = limit
        self.skip = skip
        self.remove_duplicates = remove_duplicates

        self.sort = sort

    def __str__(self):
        s  = 'First Associated [%s], ' % self.first_associated
        s += 'Last Updated [%s], ' % self.last_updated
        s += 'Owner Type [%s], ' % self.owner_type
        s += 'Owner ID [%s], ' % self.owner_id
        s += 'Limit [%s], ' % self.limit
        s += 'Skip [%s], ' % self.skip
        s += 'Sort [%s]' % self.sort
        return s

    def association_spec(self):
        spec = {}

        if self.first_associated is not None:
            spec['created'] = {self.first_associated.direction : self.first_associated.timestamp}

        if self.last_updated is not None:
            spec['updated'] = {self.last_updated.direction : self.last_updated.timestamp}

        if self.type_ids is not None:
            spec['unit_type_id'] = {'$in' : self.type_ids}

        if self.owner_type is not None:
            spec['owner_type'] = self.owner_type

        if self.owner_id is not None:
            spec['owner_id'] = self.owner_id

        return spec

class DateQueryParameter:

    BEFORE = '$lt'
    AFTER = '$gt'
    BEFORE_OR_EQUAL = '$lte'
    AFTER_OR_EQUAL = '$gte'

    def __init__(self, timestamp, direction):
        self.timestamp = timestamp
        self.direction = direction

class Fields:

    def __init__(self, field_names=None):
        if field_names is None:
            field_names = []
        self.field_names = field_names

    def add_field(self, field_name):

        self.field_names.append(field_name)
