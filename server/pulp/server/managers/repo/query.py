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

import logging

from pulp.server.exceptions import MissingResource
from pulp.server.db.model.repository import Repo, RepoDistributor, RepoImporter

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- manager ------------------------------------------------------------------

class RepoQueryManager(object):
    """
    Manager used to process user queries on repositories. Repos returned from
    these calls will be serialized to a specific format instead of simply being
    returned SON objects from the database.

    The majority of the methods below will be replaced with a single
    criteria-based find call.
    """

    def find_all(self):
        """
        Returns serialized versions of all repositories in the database.
        If there are no repositories defined, an empty list is returned.

        @return: list of serialized repositories
        @rtype:  list of dict
        """
        all_repos = list(Repo.get_collection().find())
        return all_repos

    def get_repository(self, repo_id):
        """
        Get a repository by ID.
        @param repo_id: A repository ID.
        @type repo_id: str
        @return: serialized data describing the repository
        @rtype:  dict
        @raise MissingResource: when not found
        """
        repo = self.find_by_id(repo_id)
        if repo is None:
            raise MissingResource(repo_id=repo_id)
        return repo

    def find_by_id(self, repo_id):
        """
        Returns a serialized version of the given repository if it exists.
        If a repo cannot be found with the given ID, None is returned.

        @return: serialized data describing the repository
        @rtype:  dict or None
        """
        repo = Repo.get_collection().find_one({'id' : repo_id})
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
        repos = list(Repo.get_collection().find({'id' : {'$in' : repo_id_list}}))
        return repos

    def find_with_distributor_type(self, distributor_type_id):
        """
        Returns a list of repositories, including distributor configuration,
        for all repositories that have a configured distributor of the given
        type. The distributor for each repository will be stored in the repo
        under the key "distributors".

        @return: list of repository dictionaries
        @rtype:  list
        """

        repos_by_id = {}

        repo_distributors = list(RepoDistributor.get_collection().find({'distributor_type_id' : distributor_type_id}))
        for rd in repo_distributors:
            repo = repos_by_id.get(rd['repo_id'], None)
            if repo is None:
                repo = Repo.get_collection().find_one({'id' : rd['repo_id']})
                repos_by_id[rd['repo_id']] = repo

            dists = repo.setdefault('distributors', [])
            dists.append(rd)

        return repos_by_id.values()

    def find_with_importer_type(self, importer_type_id):
        """
        Returns a list of repositories, including importer configuration,
        for all repositories that have a configured importer of the given type.
        The importer for each repository will be stored in the repo under the
        key "importer".

        @return: list of repository dictionaries
        @rtype:  list
        """

        # Only one importer per repo, so no need for supporting multiple

        results = []

        repo_importers = list(RepoImporter.get_collection().find({'importer_type_id' : importer_type_id}))
        for ri in repo_importers:
            repo = Repo.get_collection().find_one({'id' : ri['repo_id']})
            repo['importers'] = [ri]
            results.append(repo)

        return results

    @staticmethod
    def find_by_criteria(criteria):
        """
        Return a list of repositories that match the provided criteria.

        @param criteria:    A Criteria object representing a search you want
                            to perform
        @type  criteria:    pulp.server.db.model.criteria.Criteria

        @return:    list of Repo instances
        @rtype:     list
        """
        return Repo.get_collection().query(criteria)