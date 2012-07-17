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

import traceback as traceback_module

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
        self.last_publish = None
        self.scratchpad = None


class RepoGroupPublishResult(Model):

    collection_name = 'repo_group_publish_results'

    RESULT_SUCCESS = 'success'
    RESULT_FAILED = 'failed'
    RESULT_ERROR = 'error'

    @classmethod
    def error_result(cls, group_id, distributor_id, distributor_type_id, started, completed, exception, traceback):
        """
        Creates a new history entry for a failed publish. The details of the error
        raised from the plugin are captured.

        @param group_id: identifies the group
        @type  group_id: str

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

        r = cls(group_id, distributor_id, distributor_type_id, started, completed, cls.RESULT_ERROR)
        r.error_message = str(exception)
        r.exception = repr(exception)
        r.traceback = traceback_module.format_tb(traceback)

        return r

    @classmethod
    def expected_result(cls, group_id, distributor_id, distributor_type_id, started,
                        completed, summary, details):
        """
        Creates a new history entry for a successful publish.

        @param group_id: identifies the group
        @type  group_id: str

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

        r = cls(group_id, distributor_id, distributor_type_id, started, completed, cls.RESULT_SUCCESS)
        r.summary = summary
        r.details = details

        return r

    @classmethod
    def failed_result(cls, group_id, distributor_id, distributor_type_id, started,
                      completed, summary, details):
        """
        Creates a new history entry for a gracefully failed publish.

        @param group_id: identifies the group
        @type  group_id: str

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

        r = cls(group_id, distributor_id, distributor_type_id, started, completed, cls.RESULT_FAILED)
        r.summary = summary
        r.details = details

        return r

    def __init__(self, group_id, distributor_id, distributor_type_id, started, completed, result):
        """
        Describes the results of a single completed (potentially errored) publish.
        Rather than directory instantiating instances, use one of the above
        factory methods to make sure all the necessary fields are specified.
        """
        super(RepoGroupPublishResult, self).__init__()

        self.group_id = group_id
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

