"""
Contains the manager class for performing queries for repo-unit associations.
"""

import copy

import pymongo

from pulp.plugins.types import database as types_db
from pulp.server.db.model.criteria import UnitAssociationCriteria
from pulp.server.db.model.repository import RepoContentUnit


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


class RepoUnitAssociationQueryManager(object):

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

    @staticmethod
    def find_by_criteria(criteria):
        """
        Return a list of RepoContentUnits that match the provided criteria.

        @param criteria:    A Criteria object representing a search you want
                            to perform
        @type  criteria:    pulp.server.db.model.criteria.Criteria

        @return:    cursor of the query results
        @rtype:     pymongo.cursor.Cursor
        """
        return RepoContentUnit.get_collection().query(criteria)


    def get_units(self, repo_id, criteria=None, as_generator=False):
        """
        Get the units associated with the repository based on the provided unit
        association criteria.

        :param repo_id: identifies the repository
        :type  repo_id: str

        :param criteria: if specified will drive the query
        :type  criteria: UnitAssociationCriteria

        :param as_generator: if true, return a generator; if false, a list
        :type  as_generator: bool

        :return: generator or list of units associated with the repo
        :rtype: generator or list
        """

        criteria = criteria or UnitAssociationCriteria()

        unit_associations_generator = self._unit_associations_cursor(repo_id, criteria)

        if criteria.remove_duplicates:
            unit_associations_generator = self._unit_associations_no_duplicates(criteria, unit_associations_generator)

        if criteria.association_sort and not criteria.unit_filters:
            # If we're ordering by association fields, but not filtering the
            # content units, then perform the skip and limit on this generator
            # to limit the number of units we load into memory.
            # Manually perform skip and limit so we don't have to differentiate
            # based on whether we're removing duplicates or not.
            unit_associations_generator = self._with_skip_and_limit(unit_associations_generator,
                                                                    criteria.skip, criteria.limit)

        # The unit ids are used for ordering the units when association field
        # ordering is specified (i.e. created timestamps, etc.)
        # The ids are (unit_type_id, unit_id) tuples.
        association_ordered_unit_ids = []

        # The unit association information is part of the return values, so we
        # construct a lookup in order to retrieve that information when we are
        # iterating over the content units.
        #
        # unit_type_id -> unit_id -> (ordered)[association_1, association_2, ...]
        #
        # We also use the unit_id keys to lookup the units from unit_type_id
        # collections.
        associations_lookup = {}

        for association in unit_associations_generator:

            unit_type_id = association['unit_type_id']
            unit_id = association['unit_id']

            # Build the ordering.
            association_ordered_unit_ids.append((unit_type_id, unit_id))

            # Build the lookup.
            association_type_dict = associations_lookup.setdefault(unit_type_id, {})
            association_list = association_type_dict.setdefault(unit_id, [])
            association_list.append(association)

        association_unit_types = criteria.type_ids or self.unit_type_ids_for_repo(repo_id)
        # The unit types should always be sorted in the same order, this allows
        # multiple calls with skip and limit to work across types.
        association_unit_types = sorted(association_unit_types)

        # Use a generator expression here to keep from going back to the types
        # collections once we've returned our limit of results.
        # Be sure to skip cursors that would otherwise return an empty result set.
        units_cursors = (self._associated_units_by_type_cursor(t, criteria, associations_lookup[t].keys())
                         for t in association_unit_types if t in associations_lookup)

        if not criteria.association_sort:
            # If we're not sorting based on association fields, then set the
            # skip and limit individually across the cursors to get consistent
            # behavior across multiple calls across multiple unit types.
            # The order that the generators are applied here is extremely
            # important. DO NOT CHANGE!
            units_cursors = self._associated_units_cursors_with_skip(units_cursors, criteria.skip)
            units_cursors = self._associated_units_cursors_with_limit(units_cursors, criteria.limit)

        units_generator = self._units_from_chained_cursors(units_cursors)

        if criteria.association_sort:
            # Use the ordered associations we created to properly order the results.
            units_generator = self._association_ordered_units(association_ordered_unit_ids, units_generator)

            if criteria.unit_filters:
                # If we're ordering by association fields and filtering the
                # content units, then skip and limit must be performed manually
                # and last (skip and limit must always come after sorting).
                units_generator = self._with_skip_and_limit(units_generator, criteria.skip, criteria.limit)

            # The association ordering will generate the same unit for every
            # association it has with the repository, hence "duplicate units".
            units_generator = self._merged_units_duplicate_units(associations_lookup, units_generator)

        else:
            # Unit ordering or no ordering only produce unique units, hence
            # "unique units".
            units_generator = self._merged_units_unique_units(associations_lookup, units_generator)

        if as_generator:
            return units_generator

        # If as_generator isn't set, evaluate the whole pipeline by casting it
        # to a list. Should probably log this. Is there a log-level "stupid"?
        return list(units_generator)

    def get_units_across_types(self, repo_id, criteria=None, as_generator=False):
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

        :param repo_id: identifies the repository
        :type  repo_id: str

        :param criteria: if specified will drive the query
        :type  criteria: UnitAssociationCriteria

        :param as_generator: if true, return a generator; if false, a list
        :type  as_generator: bool
        """

        # This really is the new default behavior of get_units, so just pass
        # the request through.

        return self.get_units(repo_id, criteria, as_generator)

    def get_units_by_type(self, repo_id, type_id, criteria=None, as_generator=False):
        """
        Retrieves data describing units of the given type associated with the
        given repository. Information on the associations themselves is also
        provided.

        The sort fields may be from either the association data OR the
        unit fields. A mix of both is not supported. Multiple sort fields
        are supported as long as they come from the same area.

        If a sort is not provided, the units will be sorted ascending by each
        value in the unit key for the given type.

        :param repo_id: identifies the repository
        :type  repo_id: str

        :param type_id: limits returned units to the given type
        :type  type_id: str

        :param criteria: if specified will drive the query
        :type  criteria: UnitAssociationCriteria

        :param as_generator: if true, return a generator; if false, a list
        :type  as_generator: bool
        """

        # Get_units now defaults to batch behavior, so use a list of length 1 to
        # specify the unit types and pass it through.

        criteria = criteria or UnitAssociationCriteria()
        # Just overwrite the type_ids if the user was dumb enough to provide
        # them in this call.
        criteria.type_ids = [type_id]

        return self.get_units(repo_id, criteria, as_generator)

    @staticmethod
    def unit_type_ids_for_repo(repo_id):
        """
        Retrieve a list of all unit type ids currently associated with the
        repository

        :type repo_id: str
        :rtype: list
        """

        collection = RepoContentUnit.get_collection()

        cursor = collection.find({'repo_id': repo_id}, fields=['unit_type_id'])

        return [t for t in cursor.distinct('unit_type_id')]

    # -- unit association methods ----------------------------------------------

    @staticmethod
    def _unit_associations_cursor(repo_id, criteria):
        """
        Retrieve a pymongo cursor for unit associations for the given repository
        that match the given criteria.

        :type repo_id: str
        :type criteria: UnitAssociationCriteria
        :rtype: pymongo.cursor.Cursor
        """

        spec = criteria.association_filters.copy()
        spec['repo_id'] = repo_id

        if criteria.type_ids:
            spec['unit_type_id'] = {'$in': criteria.type_ids}

        collection = RepoContentUnit.get_collection()

        cursor = collection.find(spec, fields=criteria.association_fields)

        if criteria.association_sort:
            cursor.sort(criteria.association_sort)

        return cursor

    @staticmethod
    def _unit_associations_no_duplicates(criteria, cursor):
        """
        Remove duplicate unit associations from a iterator of unit associations.

        :type criteria: UnitAssociationCriteria
        :type cursor: pymongo.cursor.Cursor
        :rtype: generator
        """

        # This algorithm returns the earliest association in the case of duplicates.

        # Sorting by the "created" flag is crucial to removing duplicate associations.
        created_sort_tuple = ('created', SORT_ASCENDING)
        sort = criteria.association_sort or []
        if created_sort_tuple not in sort:
            sort.append(created_sort_tuple)
        cursor.sort(sort)

        previously_generated_association_ids = set()

        for unit_association in cursor:

            association_id = (unit_association['unit_type_id'], unit_association['unit_id'])

            if association_id in previously_generated_association_ids:
                continue

            yield unit_association

            previously_generated_association_ids.add(association_id)

    @staticmethod
    def _with_skip_and_limit(iterator, skip, limit):
        """
        Generic generator that emulates database cursor skip and limit when
        iterating over an iterator.

        The skip and limit arguments must either be None or a non-negative integer
        Skip and limit values of None and 0 are semantically equivalent.

        :type iterator: iterable
        :type skip: int or None
        :type limit: into or None
        :rtype: generator
        """
        assert (isinstance(skip, int) and skip >= 0) or skip is None
        assert (isinstance(limit, int) and limit >= 0) or limit is None

        skipped_elements = 0
        generated_elements = 0

        for element in iterator:

            if limit and generated_elements == limit:
                raise StopIteration()

            if skip and skipped_elements < skip:
                skipped_elements += 1
                continue

            yield element

            generated_elements += 1

    # -- associated units methods ----------------------------------------------

    @staticmethod
    def _associated_units_by_type_cursor(unit_type_id, criteria, associated_unit_ids):
        """
        Retrieve a pymongo cursor for units associated with a repository of a
        give unit type that meet to the provided criteria.

        :type unit_type_id: str
        :type criteria: UnitAssociationCriteria
        :type associated_unit_ids: list
        :rtype: pymongo.cursor.Cursor
        """

        collection = types_db.type_units_collection(unit_type_id)

        spec = criteria.unit_filters.copy()
        spec['_id'] = {'$in': associated_unit_ids}

        fields = criteria.unit_fields

        # The _content_type_id is required for looking up the association.
        if fields is not None and '_content_type_id' not in fields:
            fields = list(fields)
            fields.append('_content_type_id')

        cursor = collection.find(spec, fields=fields)

        sort = criteria.unit_sort

        if sort is None:
            unit_key = types_db.type_units_unit_key(unit_type_id)

            if unit_key is not None:
                sort = [(u, SORT_ASCENDING) for u in unit_key]

        if sort is not None:
            cursor.sort(sort)

        return cursor

    @staticmethod
    def _associated_units_cursors_with_skip(units_cursors, skip):
        """
        Aggressively skip as many whole cursors as possible when skip is
        specified.

        The skip argument must either be None or a non-negative integer.
        Semantically 0 and None have the same meaning: no skip

        :type units_cursors: generator of pymongo.cursor.Cursor
        :type skip: int or None
        :rtype: generator
        """
        assert (isinstance(skip, int) and skip >= 0) or skip is None

        skipped_units = 0

        for cursor in units_cursors:

            if not skip or skipped_units == skip:
                yield cursor

            elif skipped_units + cursor.count() > skip:
                to_skip = skip - skipped_units
                skipped_units += to_skip # set skipped_units to skip
                cursor.skip(to_skip)
                yield cursor

            else: # skipped_units + cursor.count() <= skip
                skipped_units += cursor.count()

    @staticmethod
    def _associated_units_cursors_with_limit(unit_cursors, limit):
        """
        Track and set the limit across multiple cursors.

        The limit argument must either be None or a non-negative integer.
        Semantically 0 and None have the same meaning: no limit

        :type unit_cursors: generator of pymongo.cursor.Cursor
        :type limit: int or None
        :rtype: generator
        """
        assert (isinstance(limit, int) and limit >= 0) or limit is None

        generated_elements = 0

        for cursor in unit_cursors:

            if not limit:
                yield cursor

            elif generated_elements == limit:
                raise StopIteration()

            elif cursor.count() + generated_elements > limit:
                to_limit = limit - generated_elements
                generated_elements += to_limit
                cursor.limit(to_limit)
                yield cursor

            else: # cursor.count() + generated_elements <= limit
                generated_elements += cursor.count()
                yield cursor

    @staticmethod
    def _units_from_chained_cursors(cursors):
        """
        Yield the individual elements from a iterator of db cursors.

        :type cursors: generator of pymongo.cursor.Cursor
        :rtype: generator
        """

        for cursor in cursors:
            for element in cursor:
                yield element

    @staticmethod
    def _association_ordered_units(associated_unit_ids, associated_units):
        """
        Return associated units in the order specified by the associated unit id
        list.

        :type associated_unit_ids: list
        :type associated_units: iterator
        :rtype: generator
        """

        # This algorithm assumes that associated_unit_ids has already been sorted.

        # XXX This is unfortunate as it's the one place that loads all of the
        # associated_units into memory.
        # It is worth noting that the units have already been filtered by type,
        # association filters, and unit filters. In addition, skip and limit
        # may have also been performed, so it's potentially not as bad as it seems.
        associated_units_by_id = dict(((u['_content_type_id'], u['_id']), u) for u in associated_units)

        for id_tuple in associated_unit_ids:
            # the associated_unit_ids are sorted, but not all of the units may
            # be in the associated_units_by_id
            if id_tuple not in associated_units_by_id:
                continue

            yield associated_units_by_id[id_tuple]

    @staticmethod
    def _merged_units_duplicate_units(associations_lookup, associated_units):
        """
        Return associated units as the unit association information and the unit
        information as metadata on the unit association information.

        Used when there are duplicate units returned by the associated_units iterator.

        :type associations_lookup: dict
        :type associated_units: iterator
        :rtype: generator
        """

        # This algorithm assumes that the units will come in the same order that
        # the associations are listed in the associations_lookup.

        for unit in associated_units:
            # Remove the associations from the list in the order they were
            # placed in it.
            association = associations_lookup[unit['_content_type_id']][unit['_id']].pop(0)
            association['metadata'] = unit
            yield association

    @staticmethod
    def _merged_units_unique_units(associations_lookup, associated_units):
        """
        Return associated units as the unit association information and the unit
        information as metadata on the unit association information.

        Used when no duplicate units returned by the associated_units iterator.

        :type associations_lookup: dict
        :type associated_units: iterator
        :rtype: generator
        """

        # This algorithm assumes that only unique units will be generated,
        # regardless of the number of times a unit is associated with a repo.

        # It also assumes that the units will be presented in the proper order
        # and the association ordering, if any, is secondary.

        for unit in associated_units:
            # Use the associations_lookup to determine how many times to return
            # the unit in the results.
            for association in associations_lookup[unit['_content_type_id']][unit['_id']]:
                # We don't want to add the unit to the associations_lookup, as that will consume a
                # large amount of RAM.
                association = association.copy()
                association['metadata'] = unit
                yield association

