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

import datetime
import traceback as traceback_module

import pulp.common.dateutils as dateutils
from pulp.server.db.model.base import Model

# -- repository classes --------------------------------------------------------

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

    @ivar content_unit_count: number of units associated with this repo. This is
                              different than the number of associations, since a
                              unit may be associated multiple times.
    @type content_unit_count: int

    @ivar metadata: arbitrary data that describes the contents of the repo;
                    the values may change as the contents of the repo change,
                    either set by the user or by an importer or distributor
    @type metadata: dict
    """

    collection_name = 'repos'
    unique_indices = ('id',)

    def __init__(self, id, display_name, description=None, notes=None, content_unit_count=0):
        super(Repo, self).__init__()

        self.id = id
        self.display_name = display_name
        self.description = description
        self.notes = notes or {}
        self.scratchpad = {} # default to dict in hopes the plugins will just add/remove from it
        self.content_unit_count = content_unit_count

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

    @ivar last_sync: timestamp of the last sync (regardless of success or failure)
                     in ISO8601 format
    @type last_sync: str
    """

    collection_name = 'repo_importers'
    unique_indices = ( ('repo_id', 'id'), )

    def __init__(self, repo_id, id, importer_type_id, config):
        super(RepoImporter, self).__init__()

        # General
        self.repo_id = repo_id
        self.id = id
        self.importer_type_id = importer_type_id
        self.config = config
        self.scratchpad = None
        self.last_sync = None
        self.scheduled_syncs = []


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

    @ivar last_publish: timestamp of the last publish (regardless of success or failure)
                        in ISO8601 format
    @type last_publish: str
    """

    collection_name = 'repo_distributors'
    unique_indices = ( ('repo_id', 'id'), )

    def __init__(self, repo_id, id, distributor_type_id, config, auto_publish):
        super(RepoDistributor, self).__init__()

        self.repo_id = repo_id
        self.id = id
        self.distributor_type_id = distributor_type_id
        self.config = config
        self.auto_publish = auto_publish
        self.scratchpad = None
        self.last_publish = None
        self.scheduled_publishes = []


class RepoContentUnit(Model):
    """
    Each instance represents a mapping between a content unit and a repo. The
    unit's metadata is stored in its appropriate type collection. A content
    unit is uniquely identified by its type (says which collection it is stored
    in) and its ID within the type collection.

    Not every content unit will have a mapping document in this collection. The
    same content unit may be mapped to multiple repos, in which case there will
    be multiple documents in this collection that reference the same unit.

    There may be multiple associations between a unit and a repository. For
    instance, associated by an importer during a sync or by a user during
    a unit copy or upload. The owner variables are used to distinguish between
    them. Queries should take this into account since in most cases the query
    will only want to know if it's associated at all, not how many times.

    @ivar repo_id: identifies the repo
    @type repo_id: str

    @ivar unit_id: ID (_id) of the content unit in its type collection
    @type unit_id: str

    @ivar unit_type_id: identifies the type of content unit being associated
    @type unit_type_id: str

    @ivar owner_type: distinguishes between importer and user initiated associations;
                      must be one of the OWNER_TYPE_* constants in this class
    @type owner_type: str

    @ivar owner_id: ID of the importer or user who created the association
    @type owner_id: str

    @ivar created: iso8601 formatted timestamp indicating when the association was first created
    @type created: str

    @ivar updated: iso8601 formatted timestamp indicating the last time the association was
                   updated (effectively when it was attempted to be created again but already existed)
    @type updated: str
    """

    collection_name = 'repo_content_units'

    # Make sure you understand how the order of these affects mongo before
    # modifying the following index
    unique_indices = ( ('repo_id', 'unit_type_id', 'unit_id', 'owner_type', 'owner_id'), )
    search_indices = ( ('repo_id', 'unit_type_id', 'owner_type'),
                       ('unit_type_id', 'created') # default sort order on get_units query, do not remove
                     )

    OWNER_TYPE_IMPORTER = 'importer'
    OWNER_TYPE_USER = 'user'

    def __init__(self, repo_id, unit_id, unit_type_id, owner_type, owner_id):
        super(RepoContentUnit, self).__init__()

        # Mapping Identity Information
        self.repo_id = repo_id
        self.unit_id = unit_id
        self.unit_type_id = unit_type_id

        # Association Metadata
        self.owner_type = owner_type
        self.owner_id = owner_id

        self.created = dateutils.format_iso8601_datetime(datetime.datetime.now())
        self.updated = self.created


class RepoSyncResult(Model):
    """
    Stores the results of a repo sync.
    """

    collection_name = 'repo_sync_results'

    RESULT_SUCCESS = 'success'
    RESULT_FAILED = 'failed'
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
        r.error_message = str(exception)
        r.exception = repr(exception)
        r.traceback = traceback_module.format_tb(traceback)

        return r

    @classmethod
    def expected_result(cls, repo_id, importer_id, importer_type_id, started, completed,
                        added_count, updated_count, removed_count, summary, details, result_code):
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

        @param updated_count: number of units updated during the sync
        @type  updated_count: int

        @param removed_count: number of units removed from the repo during the sync
        @type  removed_count: int

        @param summary: short log output from the plugin of the sync
        @type  summary: any serializable

        @param details: long log output from the plugin of the sync
        @type  details: any serializable

        @param result_code: one of the RESULT_* constants in this class
        @type  result_code: str
        """

        r = RepoSyncResult(repo_id, importer_id, importer_type_id, started, completed, result_code)
        r.added_count = added_count
        r.updated_count = updated_count
        r.removed_count = removed_count
        r.summary = summary
        r.details = details

        return r

    def __init__(self, repo_id, importer_id, importer_type_id, started, completed, result):
        """
        Describes the results of a single completed (potentially errored) sync.
        Rather than directory instantiating instances, use one of the above
        factory methods to make sure all the necessary fields are specified.
        """
        super(RepoSyncResult, self).__init__()

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
        self.updated_count = None
        self.removed_count = None
        self.summary = None
        self.details = None


class RepoPublishResult(Model):
    """
    Stores the results of a repo publish.
    """

    collection_name = 'repo_publish_results'

    RESULT_SUCCESS = 'success'
    RESULT_FAILED = 'failed'
    RESULT_ERROR = 'error'

    @classmethod
    def error_result(cls, repo_id, distributor_id, distributor_type_id, started, completed, exception, traceback):
        """
        Creates a new history entry for a failed publish. The details of the error
        raised from the plugin are captured.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param distributor_id: identifies the repo's distributor
        @type  distributor_id: str

        @param distributor_type_id: identifies the type of distributor that did the publish
        @type  distributor_type_id: str

        @param started: iso8601 formatted timestamp when the publish was begun
        @type  started: str

        @param completed: iso8601 formatted timestamp when the publish completed
        @type  completed: str

        @param exception: exception instance raised from the plugin
        @type  exception: L{Exception}

        @param traceback: traceback in the plugin that caused the exception
        @type  traceback: traceback
        """

        r = cls(repo_id, distributor_id, distributor_type_id, started, completed, cls.RESULT_ERROR)
        r.error_message = str(exception)
        r.exception = repr(exception)
        r.traceback = traceback_module.format_tb(traceback)

        return r

    @classmethod
    def expected_result(cls, repo_id, distributor_id, distributor_type_id, started,
                        completed, summary, details, result_code):
        """
        Creates a new history entry for a successful publish.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param distributor_id: identifies the repo's distributor
        @type  distributor_id: str

        @param distributor_type_id: identifies the type of distributor that did the publish
        @type  distributor_type_id: str

        @param started: iso8601 formatted timestamp when the publish was begun
        @type  started: str

        @param completed: iso8601 formatted timestamp when the publish completed
        @type  completed: str

        @param summary: short log output from the plugin of the publish
        @type  summary: any serializable

        @param details: long log output from the plugin of the publish
        @type  details: any serializable

        @param result_code: one of the RESULT_* constants in this class
        @type  result_code: str
        """

        r = cls(repo_id, distributor_id, distributor_type_id, started, completed, result_code)
        r.summary = summary
        r.details = details

        return r

    @classmethod
    def failed_result(cls, repo_id, distributor_id, distributor_type_id, started, completed, summary, details):
        """
        Creates a new history entry for a gracefully failed publish.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param distributor_id: identifies the repo's distributor
        @type  distributor_id: str

        @param distributor_type_id: identifies the type of distributor that did the publish
        @type  distributor_type_id: str

        @param started: iso8601 formatted timestamp when the publish was begun
        @type  started: str

        @param completed: iso8601 formatted timestamp when the publish completed
        @type  completed: str

        @param summary: short log output from the plugin of the publish
        @type  summary: any serializable

        @param details: long log output from the plugin of the publish
        @type  details: any serializable
        """

        r = cls(repo_id, distributor_id, distributor_type_id, started, completed, cls.RESULT_FAILED)
        r.summary = summary
        r.details = details

        return r

    def __init__(self, repo_id, distributor_id, distributor_type_id, started, completed, result):
        """
        Describes the results of a single completed (potentially errored) publish.
        Rather than directory instantiating instances, use one of the above
        factory methods to make sure all the necessary fields are specified.
        """
        super(RepoPublishResult, self).__init__()

        self.repo_id = repo_id
        self.distributor_id = distributor_id
        self.distributor_type_id = distributor_type_id
        self.started = started
        self.completed = completed
        self.result = result

        # Include the success/error specific fields so they appear in all cases
        self.error_message = None
        self.exception = None
        self.traceback = None

        self.summary = None
        self.details = None
