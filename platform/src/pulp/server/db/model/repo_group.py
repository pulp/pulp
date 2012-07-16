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

from pulp.server.db.model.base import Model

class RepoGroup(Model):
    """
    Represents a group of repositories for doing batch queries and operations
    """

    collection_name = 'repo_groups'

    unique_indices = ('id',)
    search_indices = ('display_name', 'repo_ids')

    def __init__(self, id, display_name=None, description=None, repo_ids=None, notes=None):
        super(RepoGroup, self).__init__()

        self.id = id
        self.display_name = display_name
        self.description = description
        self.repo_ids = repo_ids or []
        self.notes = notes or {}

        self.scratchpad = None


class RepoGroupDistributor(Model):
    """
    Represents group-wide distributors.
    """

    collection_name = 'repo_group_distributors'

    unique_indices = (('repo_group_id', 'id'),)
    search_indices = ('distributor_type_id', 'repo_group_id', 'id')

    def __init__(self, id, distributor_type_id, repo_group_id, config):
        super(RepoGroupDistributor, self).__init__()

        self.id = id
        self.distributor_type_id = distributor_type_id
        self.repo_group_id = repo_group_id
        self.config = config

        self.scratchpad = None