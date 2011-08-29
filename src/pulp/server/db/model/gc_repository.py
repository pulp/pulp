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

from pulp.server.db.model.base import Model

# -- classes -----------------------------------------------------------------

class Repo(Model):

    collection_name = 'gc_repositories'
    unique_indices = ('id',)

    def __init__(self, id, display_name, description=None, notes=None):

        # Don't call super.__init__ since it generates a UUID

        # General
        self.id = id
        self._id = id
        self.display_name = display_name
        self.description = description
        self.notes = notes or {}

        # Cloning
        self.clone_ids = []
        self.clone_filters = []

        # Units
        self.content_units = []
        self.content_unit_count = 0

        # Importers
        #   While the APIs only allow for single importer per repo, we store
        #   them as a mapping of ID to importer for future compatibility if
        #   we lift that restriction
        self.importers = {} # importer ID to RepoImporter instance

        # Distributors
        self.distributors = {} # distributor id to RepoDistributor instance

class RepoImporter(Model):
    """
    Definition of an importer assigned to a repository. This couples the type of
    importer being used with the configuration for it for a given repository.
    This is effectively an "instance" of an importer.
    """

    collection_name = 'gc_repo_importers'
    unique_indicies = ( ('repo_id', 'id'), )

    def __init__(self, repo_id, id, importer_type_id, config):

        # Generate a UUID for _id
        Model.__init__(self)

        # General
        self.repo_id = repo_id
        self.id = id
        self.importer_type_id = importer_type_id
        self.config = config

        # Sync
        self.sync_in_progress = False
        self.last_sync = None # ISO8601 formatted string (see dateutils)

class RepoDistributor(Model):
    """
    Definition of a distributor assigned to a repository. This couples the type
    of distributor with the configuration it will use for a given repository.
    This is effectively an "instance" of a distributor.
    """

    collection_name = 'gc_repo_distributors'
    unique_indices = ( ('repo_id', 'id'), )

    def __init__(self, repo_id, id, distributor_type_id, config, auto_distribute):

        # Generate a UUID for _id
        Model.__init__(self)

        self.repo_id = repo_id
        self.id = id

        self.distributor_type_id = distributor_type_id
        self.config = config

        self.auto_distribute = auto_distribute