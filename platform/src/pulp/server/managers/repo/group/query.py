# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
from pulp.server.db.model.repo_group import RepoGroup, RepoGroupDistributor

from pulp.server.exceptions import MissingResource

class RepoGroupQueryManager(object):

    def get_group(self, repo_group_id):
        """
        Returns the repository group with the given ID, raising an exception
        if one does not exist.

        @param repo_group_id: identifies the group
        @type  repo_group_id: str

        @return: database representation of the repo group

        @raise MissingResource: if there is no group with the given ID
        """
        group = RepoGroup.get_collection().find_one({'id' : repo_group_id})
        if group is None:
            raise MissingResource(repo_group=repo_group_id)
        return group

    def find_all(self):
        """
        Returns all repository groups in the database or an empty list if
        none exist.

        @return: list of database representations of all repository groups
        @rtype:  list
        """
        groups = list(RepoGroup.get_collection().find())
        return groups

    def find_with_distributor_type(self, distributor_type_id):
        """
        Returns a list of repository groups, including a list of distributor
        instances, for all groups that have a configured distributor of the
        given type. The distributor list will be stored in the group under
        the key "distributors"

        @return: list of group objects from the database with an extra key
                 added holding the distributor instances
        """

        group_coll = RepoGroup.get_collection()
        group_distributor_coll = RepoGroupDistributor.get_collection()

        groups_by_id = {}

        spec = {'distributor_type_id' : distributor_type_id}
        group_distributors = list(group_distributor_coll.find(spec))
        for gd in group_distributors:
            group = groups_by_id.get(gd['repo_group_id'], None)
            if group is None:
                group = group_coll.find_one({'id' : gd['repo_group_id']})
                groups_by_id[gd['repo_group_id']] = group

            dists = group.setdefault('distributors', [])
            dists.append(gd)

        return groups_by_id.values()