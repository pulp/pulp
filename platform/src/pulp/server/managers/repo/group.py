# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied, including the
# implied warranties of MERCHANTABILITY, NON-INFRINGEMENT, or FITNESS FOR A
# PARTICULAR PURPOSE.
# You should have received a copy of GPLv2 along with this software; if not,
# see http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import sys

from pymongo.errors import DuplicateKeyError

from pulp.server import exceptions as pulp_exceptions
from pulp.server.db.model.repository import Repo, RepoGroup


class RepoGroupManager(object):

    # cud operations -----------------------------------------------------------

    def create_repo_group(self, group_id, display_name=None, description=None, repo_ids=None, notes=None):
        collection = RepoGroup.get_collection()
        repo_group = RepoGroup(group_id, display_name, description, repo_ids, notes)
        try:
            collection.insert(repo_group, safe=True)
        except DuplicateKeyError:
            raise pulp_exceptions.DuplicateResource(group_id), None, sys.exc_info()[2]
        group = collection.find_one({'id': group_id})
        return group

    def update_repo_group(self, group_id, **updates):
        collection = validate_existing_repo_group(group_id)
        keywords = updates.keys()
        valid_keywords = ('display_name', 'description', 'notes')
        invalid_keywords = []
        for kw in keywords:
            if kw in valid_keywords:
                continue
            invalid_keywords.append(kw)
        if invalid_keywords:
            raise pulp_exceptions.InvalidValue(invalid_keywords)
        collection.update({'id': group_id}, {'$set': updates}, safe=True)
        group = collection.find_one({'id': group_id})
        return group

    def delete_repo_group(self, group_id):
        collection = validate_existing_repo_group(group_id)
        collection.remove({'id': group_id}, safe=True)

    # repo membership ----------------------------------------------------------

    def remove_repo_from_groups(self, repo_id, group_ids=None):
        """
        Remove a repo from the list of repo groups provided. If no repo groups
        are specified, remove the repo from all repo groups its currently in.
        (idempotent: useful when deleting repositories)
        @param repo_id: unique id of the repo to remove from repo groups
        @type  repo_id: str
        @param group_ids: list of repo group ids to remove the repo from
        @type  group_ids: list of None
        """
        spec = {}
        if group_ids is not None:
            spec = {'id': {'$in': group_ids}}
        collection = RepoGroup.get_collection()
        collection.update(spec, {'$pull': {'repo_ids': repo_id}}, multi=True, safe=True)

    def associate(self, group_id, criteria):
        """
        Associate a set of repos to the group that match the passed in criteria.
        @param group_id: unique id of the group to associate repos to
        @type  group_id: str
        @param criteria: Criteria instance representing the set of repos to associate
        @type  criteria: L{pulp.server.db.model.criteria.Criteria}
        """
        group_collection = validate_existing_repo_group(group_id)
        repo_collection = Repo.get_collection()
        cursor = repo_collection.query(criteria)
        repo_ids = [r['id'] for r in cursor]
        if not repo_ids:
            return
        group_collection.update({'id': group_id},
                                {'$addToSet': {'repo_ids': {'$each': repo_ids}}},
                                safe=True)

    def unassociate(self, group_id, criteria):
        """
        Unassociate a set of repos from the group that match the passed in criteria.
        @param group_id: unique id of the group to unassociate repos from
        @type  group_id: str
        @param criteria: Criteria instance representing the set of repos to unassociate
        @type  criteria: L{pulp.server.db.model.criteria.Criteria}
        """
        group_collection = validate_existing_repo_group(group_id)
        repo_collection = Repo.get_collection()
        cursor = repo_collection.query(criteria)
        repo_ids = [r['id'] for r in cursor]
        if not repo_ids:
            return
        group_collection.update({'id': group_id},
                                # for some reason, pymongo 1.9 doesn't like this
                                #{'$pull': {'repo_ids': {'$in': repo_ids}}},
                                {'$pullAll': {'repo_ids': repo_ids}},
                                safe=True)

    # notes --------------------------------------------------------------------

    def add_notes(self, group_id, notes):
        group_collection = validate_existing_repo_group(group_id)
        set_doc = dict(('notes.' + k, v) for k, v in notes.items())
        group_collection.update({'id': group_id}, {'$set': set_doc}, safe=True)

    def remove_notes(self, group_id, keys):
        group_collection = validate_existing_repo_group(group_id)
        unset_doc = dict(('notes.' + k, 1) for k in keys)
        group_collection.update({'id': group_id}, {'$unset': unset_doc}, safe=True)

    def set_note(self, group_id, key, value):
        self.add_notes(group_id, {key: value})

    def unset_note(self, group_id, key):
        self.remove_notes(group_id, [key])

# utility functions ------------------------------------------------------------

def validate_existing_repo_group(group_id):
    """
    Validate the existence of a repo group, given its id.
    Returns the repo group db collection upon successful validation,
    raises an exception upon failure
    @param group_id: unique id of the repo group to validate
    @type  group_id: str
    @return: repo group db collection
    @rtype:  L{pulp.server.db.connection.PulpCollection}
    @raise:  L{pulp.server.exceptions.MissingResource}
    """
    collection = RepoGroup.get_collection()
    repo_group = collection.find_one({'id': group_id})
    if repo_group is not None:
        return collection
    raise pulp_exceptions.MissingResource(repo_group=group_id)
