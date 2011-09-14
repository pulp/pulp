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
Contains the manager class and exceptions for searching for repositories.
"""

from gettext import gettext as _
import logging

from pulp.server.db.model.gc_repository import Repo, RepoDistributor, RepoImporter

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- manager ------------------------------------------------------------------

class RepoQueryManager:
    """
    Manager used to process user queries on repositories. Repos returned from
    these calls will be serialized to a specific format instead of simply being
    returned SON objects from the database.
    """

    def find_all(self):
        """
        Returns serialized versions of all repositories in the database.
        If there are no repositories defined, an empty list is returned.

        @return: list of serialized repositories
        @rtype:  list of dict
        """
        all_repos = list(Repo.get_collection().find())
        serialized_repos = []
        for r in all_repos:
            serialized = _serialize_repo(r)
            serialized_repos.append(serialized)

        return serialized_repos

    def find_by_id(self, repo_id):
        """
        Returns a serialized version of the given repository if it exists.
        If a repo cannot be found with the given ID, None is returned.

        @return: serialized data describing the repository
        @rtype:  dict or None
        """
        repo = Repo.get_collection().find_one({'id' : repo_id})
        if repo is not None:
            repo = _serialize_repo(repo)

        return repo
            
    def find_by_id_list(self, repo_id_list):
        """
        Returns serialized versions of all of the given repositories. Any
        IDs that do not refer to valid repositories are ignored and will not
        raise an error.

        @param repo_id_list: list of repo IDs to fetch
        @type  repo_id_list: list of str

        @return: list of serialized repositories
        @rtype:  list of dict
        """
        repos = Repo.get_collection().find({'id' : {'$in' : repo_id_list}})
        serialized_repos = []
        for r in repos:
            serialized = _serialize_repo(r)
            serialized_repos.append(serialized)

        return serialized_repos

    def find_by_notes(self, notes):
        pass

    def find_by_supported_type(self, type_name):
        pass

    def find_by_content_unit(self, unit_id):
        pass

def _serialize_repo(repo):
    """
    Takes a Pulp repository SON object and converts it to a standard query
    result format.

    @param repo: repo object in SON format out of the database
    @type  repo: dict

    @return: serialized version of the repo suitable for returning from queries
    @rtype:  dict
    """

    summary = {
        'id' : repo['id'],
        'display_name' : repo['display_name'],
        'description' : repo['description'],
        'notes' : repo['notes'],
        'content_unit_count' : repo['content_unit_count']
    }

    return summary
