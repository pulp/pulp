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

import json

from operator import itemgetter
from hashlib import sha256

from pulp.server.config import config as pulp_conf
from pulp.server.db import connection
from pulp.server.db.model.repository import Repo, RepoDistributor, RepoContentUnit
from pulp.plugins.types.database import type_units_collection

from pulp_node import constants


# --- constants --------------------------------------------------------------


REPO_FIELDS = ('id', 'display_name', 'description', 'notes')
DIST_FIELDS = ('repo_id', 'distributor_type_id', 'id', 'config')
UNIT_FIELDS = ('repo_id', 'unit_id', 'unit_type_id')

REPO_SORT = itemgetter('id')
DIST_SORT = itemgetter('repo_id', 'distributor_type_id', 'id')
UNIT_SORT = itemgetter('repo_id', 'unit_fingerprint')


# --- API --------------------------------------------------------------------


def build_profile(repo_ids=None):
    """
    Build a nodes profile by interrogating the pulp DB.
    Use init() to initialize the DB as needed.
    :param repo_ids: When specified, the profile is restricted to include
        only the specified repositories.  When not specified, all repositories are included.
        The contents of the profile are sorted to to better support profile comparisons.
        See constants for sorting details.
    :rtype repo_ids: list
    :return: The node profile.
    :rtype: dict
    """
    init_db()
    repositories = fetch_repositories(repo_ids)
    repo_ids = repositories.keys()
    distributors = fetch_distributors(repo_ids)
    unit_associations = fetch_unit_associations(repo_ids)
    for unit_id, unit in fetch_units(unit_associations.values()):
        unit_association = unit_associations[unit_id]
        unit_association.pop('unit_id')
        unit_association[constants.PROFILE_UNIT_FINGERPRINT] = fingerprint(unit)
    repositories = repositories.values()
    unit_associations = unit_associations.values()
    repositories.sort(key=REPO_SORT)
    distributors.sort(key=DIST_SORT)
    unit_associations.sort(key=UNIT_SORT)
    collate(repositories, distributors, unit_associations)
    return {constants.PROFILE_REPOSITORIES: repositories}


# --- utils ------------------------------------------------------------------


def init_db():
    """
    Initialize the DB.
    """
    if connection._connection is None:
        name = pulp_conf.get('database', 'name')
        connection.initialize(name)


def fingerprint(thing):
    """
    Generate a unique fingerprint of the specified object.
    :param thing: An object to fingerprint.
    :type thing: object
    :return: The generated fingerprint.
    """
    json_thing = json.dumps(thing, separators=(',', ':'), sort_keys=True)
    _hash = sha256()
    _hash.update(json_thing)
    return _hash.hexdigest()


def collate(repositories, distributors, units):
    """
    Collate the specified distributors and content units within their associated repository.
    :param repositories: A list of repositories.
    :param distributors: A list of distributors.
    :param units: A list of content units.
    """
    for repo in repositories:
        repo_id = repo['id']
        _distributors = [d for d in distributors if d['repo_id'] == repo_id]
        _units = [u for u in units if u['repo_id'] == repo_id]
        repo[constants.PROFILE_DISTRIBUTORS] = _distributors
        repo[constants.PROFILE_UNITS] = _units


def strip(son):
    """
    Remove unwanted json artifacts that are not portable between pulp installations.
    For example: _id, _namespace.
    :param son: A SON object retried from the DB.
    :return: The stripped object.
    :rtype: dict
    """
    for key in son.keys():
        if not key.startswith('_'):
            continue
        son.pop(key, 0)
    return dict(son)


def fetch_repositories(repo_ids=None):
    """
    Fetch repositories from the DB.
    :param repo_ids: When specified, the profile is restricted to include
        only the specified repositories.  When not specified, all repositories are included.
        The contents of the profile are sorted to to better support profile comparisons.
    :rtype repo_ids: list
    :return: A dictionary of stripped repositories keyed by repo_id.
    :rtype: dict
    """
    if repo_ids is None:
        query = {}  # ALL
    else:
        query = {'id': {'$in': repo_ids}}
    fetched = {}
    collection = Repo.get_collection()
    for r in collection.find(query, fields=REPO_FIELDS):
        fetched[r['id']] = strip(r)
    return fetched


def fetch_distributors(repo_ids):
    """
    Fetch repository-distributors from the DB.
    :param repo_ids: When specified, the profile is restricted to include
        only the specified repositories.  When not specified, all repositories are included.
        The contents of the profile are sorted to to better support profile comparisons.
    :rtype repo_ids: list
    :return: A list of repository-distributors.
    :rtype: list
    """
    fetched = []
    query = {'repo_id': {'$in': repo_ids}}
    collection = RepoDistributor.get_collection()
    for d in collection.find(query, fields=DIST_FIELDS):
        type_id = d['distributor_type_id']
        if type_id in constants.ALL_DISTRIBUTORS:
            continue
        fetched.append(strip(d))
    return fetched


def fetch_unit_associations(repo_ids):
    """
    Fetch content units from the DB.
    :param repo_ids: When specified, the profile is restricted to include
        only the specified repositories.  When not specified, all repositories are included.
        The contents of the profile are sorted to to better support profile comparisons.
    :rtype repo_ids: list
    :return: A dictionary of unit-associations keyed by unit_id.
    :rtype: dict
    """
    fetched = {}
    query = {'repo_id': {'$in': repo_ids}}
    collection = RepoContentUnit.get_collection()
    for u in collection.find(query, fields=UNIT_FIELDS):
        unit_id = u['unit_id']
        fetched[unit_id] = strip(u)
    return fetched


def fetch_units(unit_associations):
    """
    Generator used to fetch the content units associated with the
    specified unit-associations.
    :param unit_associations: A list of unit associations.
    :type unit_associations: list
    :return: unit_id, stripped unit
    :rtype: tuple(2)
    """
    for cursor in unit_cursors(unit_associations):
        for u in cursor:
            unit_id = u['_id']
            yield unit_id, strip(u)


def unit_types(unit_associations):
    """
    Get a dictionary of unit_id lists keyed by unit type_id.
    :param unit_associations: A list of unit associations.
    :type unit_associations: list
    :return: A dictionary of unit_id lists keyed by unit type_id.
    """
    types = {}
    for u in unit_associations:
        type_id = u['unit_type_id']
        unit_id = u['unit_id']
        unit_ids = types.setdefault(type_id, [])
        unit_ids.append(unit_id)
    return types


def unit_cursors(unit_associations):
    """
    Generator used open cursors to all unit collections based on type_id.
    Each cursor is opened using a query containing only the unit_ids needed
    from each collection based on the unit-associations.
    :param unit_associations: A list of unit associations.
    :type unit_associations: list
    :return: Open cursors.
    """
    types = unit_types(unit_associations)
    for type_id, unit_ids in types.items():
        query = {'_id': {'$in': unit_ids}}
        collection = type_units_collection(type_id)
        cursor = collection.find(query)
        yield cursor


# --- testing ----------------------------------------------------------------


def test_1():
    p = build_profile()
    repositories = p[constants.PROFILE_REPOSITORIES]
    print '-- Repositories [%.2d] --------------------------------' % len(repositories)
    for r in repositories:
        print r


def test_2():
    from pprint import pprint
    p = build_profile()
    p2 = build_profile()
    pprint(p)
    print fingerprint(p) == fingerprint(p2)


if __name__ == '__main__':
    test_2()
    test_1()