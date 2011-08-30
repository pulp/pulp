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
    """
    Represents a Pulp repository. Instances of this class will have references
    into the repo importer and repo distributor collections that will describe
    the actual functionality provided by the repository.

    @ivar id: unique across all repos
    @type id: str

    @ivar display_name: user-readable name of the repository
    @type display_name: str

    @ivar description: free form text provided by the user to describe the repo
    @type description: str

    @ivar notes: arbitrary key-value pairs programmatically describing the repo
    @type notes: dict

    @ivar clone_ids: list of repo IDs for repos cloned from this instance
    @type clone_ids: list of str

    @ivar clone_filters: list of filters applied when cloning this repo; each
                         entry is the ID of a document in the Filter collection
    @type clone_filters: list of str

    @ivar content_units: list of references from this repo to content units in it
    @type content_units: to be determined

    @ivar content_unit_count: number of content units in the repo
    @type content_unit_count: int

    @ivar importers: mapping of importer ID to document in the RepoImporter collection
                     of all importers being used by this repo; each importer ID
                     must be unique within a given repo
    @type importers: dict: str, L{RepoImporter}

    @ivar distributors: mapping of distributor ID to document in the RepoDistributor
                        collection of all distributors being used by this repo;
                        each distributor ID must be unique within a given repo
    @type distributors: dict: str, L{RepoDistributor}
    """

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
        # TODO: track when this association was updated per unit
        # TODO: more important, figure out what this relationship looks like
        self.content_units = []
        self.content_unit_count = 0

        # Timeline
        # TODO: figure out how to track repo modified states

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

    Each RepoImporter is uniquely identified by the tuple of ID and repo ID.

    @ivar repo_id: identifies the repo to which it is associated
    @type repo_id: str

    @ivar id: uniquely identifies this instance for the repo it's associated with
    @type id: str

    @ivar importer_type_id: used to look up the importer plugin when this
                            importer is used
    @type importer_type_id: str

    @ivar config: importer config passed to the plugin when it is invoked
    @type config: dict
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

    Each RepoDistributor is uniquely identified by the tuple of ID and repo ID.

    @ivar repo_id: identifies the repo to which it is associated
    @type repo_id: str

    @ivar id: uniquely identifies this instance for the repo it's associated with
    @type id: str

    @ivar distributor_type_id: used to look up the distributor plugin when this
                               importer is used
    @type distributor_type_id: str

    @ivar config: distributor config passed to the plugin when it is invoked
    @type config: dict
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