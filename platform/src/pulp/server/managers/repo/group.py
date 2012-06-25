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
from pulp.server.db.model.repository import RepoGroup


class RepoGroupManager(object):

    # cud operations -----------------------------------------------------------

    def create_repo_group(self, group_id, display_name=None, description=None, repo_ids=None, notes=None):
        collection = RepoGroup.get_collection()
        repo_group = RepoGroup(group_id, display_name, description, repo_ids, notes)
        try:
            collection.insert(repo_group, safe=True)
        except DuplicateKeyError:
            raise pulp_exceptions.DuplicateResource(group_id), None, sys.exc_info()[2]

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

    def delete_repo_group(self, group_id):
        collection = RepoGroup.get_collection()
        collection.remove({'id': group_id}, safe=True)

    # repo membership ----------------------------------------------------------

    def add_repo_to_group(self, group_id, repo_id):
        collection = validate_existing_repo_group(group_id)
        collection.update({'id': group_id, 'repo_ids': {'$ne': repo_id}},
                          {'$push': {'repo_ids': repo_id}},
                          safe=True)

    def remove_repo_from_group(self, group_id, repo_id):
        collection = validate_existing_repo_group(group_id)
        collection.update({'id': group_id, 'repo_ids': {'$eq': repo_id}},
                          {'$pull': {'repo_ids': repo_id}},
                          safe=True)

# utility functions ------------------------------------------------------------

def validate_existing_repo_group(group_id):
    collection = RepoGroup.get_collection()
    repo_group = collection.find_one({'id': group_id})
    if repo_group is not None:
        return collection
    raise pulp_exceptions.MissingResource(repo_group=group_id)
