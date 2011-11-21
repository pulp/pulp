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

import traceback as traceback_module

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

    @ivar notes: arbitrary key-value pairs programmatically describing the repo;
                 these are intended as a way to describe the repo usage or
                 organizational purposes and should not vary depending on the
                 actual content of the repo
    @type notes: dict

    @ivar metadata: arbitrary data that describes the contents of the repo;
                    the values may change as the contents of the repo change,
                    either set by the user or by an importer or distributor
    @type metadata: dict

    @ivar content_unit_count: number of content units in the repo
    @type content_unit_count: int
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

        # Content
        self.content_unit_count = 0

        # Timeline
        # TODO: figure out how to track repo modified states

        # Importers, Distributors, and Content Units are not referenced from
        # repo instances. They are retrieved separately through their respective
        # collections.

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

    @ivar scratchpad: free-form field for the importer plugin to use to store
                      whatever it needs (keep in mind this instance is scoped to
                      a particular repo)
    @type scratchpad: anything pickle-able

    @ivar sync_in_progress: holds the state of the importer
    @type sync_in_progress: bool

    @ivar last_sync: timestamp of the last sync (regardless of success or failure)
                     in ISO8601 format
    @type last_sync: str
    """

    collection_name = 'gc_repo_importers'
    unique_indices = ( ('repo_id', 'id'), )

    def __init__(self, repo_id, id, importer_type_id, config):

        # Generate a UUID for _id
        Model.__init__(self)

        # General
        self.repo_id = repo_id
        self.id = id
        self.importer_type_id = importer_type_id
        self.config = config
        self.scratchpad = None

        # Sync
        self.sync_in_progress = False
        self.last_sync = None

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

    @ivar scratchpad: free-form field for the distributor plugin to use to store
                      whatever it needs (keep in mind this instance is scoped to
                      a particular repo)
    @type scratchpad: anything pickle-able

    @ivar auto_publish: indicates if the distributor should automatically
                        publish the repo on the tail end of a successful sync
    @type auto_publish: bool

    @ivar publish_in_progress: holds the state of the distributor
    @type publish_in_progress: bool

    @ivar last_publish: timestamp of the last publish (regardless of success or failure)
                        in ISO8601 format
    @type last_publish: str
    """

    collection_name = 'gc_repo_distributors'
    unique_indices = ( ('repo_id', 'id'), )

    def __init__(self, repo_id, id, distributor_type_id, config, auto_publish):

        # Generate a UUID for _id
        Model.__init__(self)

        self.repo_id = repo_id
        self.id = id
        self.distributor_type_id = distributor_type_id
        self.config = config
        self.auto_publish = auto_publish
        self.scratchpad = None

        # Publish
        self.publish_in_progress = False
        self.last_publish = None

class RepoContentUnit(Model):
    """
    Each instance represents a mapping between a content unit and a repo. The
    unit's metadata is stored in its appropriate type collection. A content
    unit is uniquely identified by its type (says which collection it is stored
    in) and its ID within the type collection.

    Not every content unit will have a mapping document in this collection. The
    same content unit may be mapped to multiple repos, in which case there will
    be multiple documents in this collection that reference the same unit.

    @ivar repo_id: identifies the repo
    @type repo_id: str

    @ivar unit_id: ID (_id) of the content unit in its type collection
    @type unit_id: str

    @ivar unit_type_id: identifies the type of content unit being associated
    @type unit_type_id: str
    """

    collection_name = 'gc_repo_content_unit'
    unique_indices = ( ('repo_id', 'unit_id', 'unit_type_id'), )

    def __init__(self, repo_id, unit_id, unit_type_id):

        # Generate a UUID for _id
        Model.__init__(self)

        # Mapping Identity Information
        self.repo_id = repo_id
        self.unit_id = unit_id
        self.unit_type_id = unit_type_id

        # Association Metadata
        #   We can add extra information about the relationship between the
        #   repo and the content unit in this collection. For instance, if
        #   we want to track when the association was made.

class RepoSyncResult(Model):
    """
    Stores the results of a repo sync.
    """

    collection_name = 'gc_repo_sync_result'

    RESULT_SUCCESS = 'success'
    RESULT_ERROR = 'error'

    @classmethod
    def error_result(cls, repo_id, importer_id, importer_type_id, started, completed, exception, traceback):
        """
        Creates a new history entry for a failed sync. The details of the error
        raised from the plugin are captured.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param importer_id: identifies the repo's importer
        @type  importer_id: str

        @param importer_type_id: identifies the type of importer that did the sync
        @type  importer_type_id: str

        @param started: iso8601 formatted timestamp when the sync was begun
        @type  started: str

        @param completed: iso8601 formatted timestamp when the sync completed
        @type  completed: str

        @param exception: exception instance raised from the plugin
        @type  exception: L{Exception}

        @param traceback: traceback in the plugin that caused the exception
        @type  traceback: traceback
        """

        r = RepoSyncResult(repo_id, importer_id, importer_type_id, started, completed, RepoSyncResult.RESULT_ERROR)
        r.error_message = exception[0]
        r.exception = repr(exception)
        r.traceback = traceback_module.format_tb(traceback)

        return r

    @classmethod
    def success_result(cls, repo_id, importer_id, importer_type_id, started, completed, added_count, removed_count, plugin_log):
        """
        Creates a new history entry for a successful sync.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param importer_id: identifies the repo's importer
        @type  importer_id: str

        @param importer_type_id: identifies the type of importer that did the sync
        @type  importer_type_id: str

        @param started: iso8601 formatted timestamp when the sync was begun
        @type  started: str

        @param completed: iso8601 formatted timestamp when the sync completed
        @type  completed: str

        @param added_count: number of new units added during the sync
        @type  added_count: int

        @param removed_count: number of units removed from the repo during the sync
        @type  removed_count: int

        @param plugin_log: log output from the plugin of the sync
        @type  plugin_log: str
        """

        r = RepoSyncResult(repo_id, importer_id, importer_type_id, started, completed, RepoSyncResult.RESULT_SUCCESS)
        r.added_count = added_count
        r.removed_count = removed_count
        r.plugin_log = plugin_log

        return r

    def __init__(self, repo_id, importer_id, importer_type_id, started, completed, result):
        """
        Describes the results of ya single completed (potentially errored) sync.
        Rather than directory instantiating instances, use one of the above
        factory methods to make sure all the necessary fields are specified.
        """
        Model.__init__(self)

        self.repo_id = repo_id
        self.importer_id = importer_id
        self.importer_type_id = importer_type_id
        self.started = started
        self.completed = completed
        self.result = result

        # Include the success/error specific fields so they appear in all cases
        self.error_message = None
        self.exception = None
        self.traceback = None

        self.added_count = None
        self.removed_count = None
        self.plugin_log = None