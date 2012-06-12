# -*- coding: utf-8 -*-
#
# Copyright © 2011-2012 Red Hat, Inc.
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
Contains the manager class and exceptions for performing repository sync
operations. All classes and functions in this module run synchronously; any
need to execute syncs asynchronously must be handled at a higher layer.
"""

# Python
import datetime
from gettext import gettext as _
import logging
import os
import pymongo
import sys

# Pulp
from pulp.common import dateutils
import pulp.server.constants as pulp_constants
import pulp.plugins.loader as plugin_loader
from pulp.plugins.conduits.repo_sync import RepoSyncConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import SyncReport
from pulp.server.db.model.repository import Repo, RepoImporter, RepoSyncResult
import pulp.server.managers.factory as manager_factory
import pulp.server.managers.repo._common as common_utils
from pulp.server.exceptions import MissingResource, PulpExecutionException

# TODO: This needs to change because managers shouldn't reach into each other
# or else we'll run back into circular imports again.
from pulp.server.managers.repo.unit_association import OWNER_TYPE_IMPORTER


# -- constants ----------------------------------------------------------------

REPO_STORAGE_DIR = os.path.join(pulp_constants.LOCAL_STORAGE, 'repos')

_LOG = logging.getLogger(__name__)

# -- manager ------------------------------------------------------------------

class RepoSyncManager(object):
    """
    Manager used to handle sync and sync query operations.
    """

    def sync(self, repo_id, sync_config_override=None):
        """
        Performs a synchronize operation on the given repository.

        The given repo must have an importer configured. The identity of the
        importer is not a parameter to this call; if multiple importers are
        eventually supported this will have to change to indicate which
        importer to use.

        This method is intentionally limited to synchronizing a single repo.
        Performing multiple repository syncs concurrently will require a more
        global view of the server and must be handled outside the scope of this
        class.

        @param repo_id: identifies the repo to sync
        @type  repo_id: str

        @param sync_config_override: optional config containing values to use
                                     for this sync only
        @type  sync_config_override: dict

        @raise MissingResource: if repo_id does not refer to a valid repo
        @raise OperationFailed: if the given repo does not have an importer set
        """

        repo_coll = Repo.get_collection()
        importer_coll = RepoImporter.get_collection()
        sync_result_coll = RepoSyncResult.get_collection()

        # Validation
        repo = repo_coll.find_one({'id' : repo_id})
        if repo is None:
            raise MissingResource(repo_id)

        repo_importers = list(importer_coll.find({'repo_id' : repo_id}))

        if len(repo_importers) is 0:
            raise PulpExecutionException()
        repo_importer = repo_importers[0]

        try:
            importer_instance, plugin_config = plugin_loader.get_importer_by_id(repo_importer['importer_type_id'])
        except plugin_loader.PluginNotFound:
            raise MissingResource(repo_id), None, sys.exc_info()[2]

        # Assemble the data needed for the sync
        conduit = RepoSyncConduit(repo_id, repo_importer['id'], OWNER_TYPE_IMPORTER, repo_importer['id'])

        call_config = PluginCallConfiguration(plugin_config, repo_importer['config'], sync_config_override)
        transfer_repo = common_utils.to_transfer_repo(repo)
        transfer_repo.working_dir = common_utils.importer_working_dir(repo_importer['importer_type_id'], repo_id, mkdir=True)

        # Perform the sync
        sync_start_timestamp = _now_timestamp()
        try:
            importer_coll.save(repo_importer, safe=True)
            sync_report = importer_instance.sync_repo(transfer_repo, conduit, call_config)
        except Exception, e:
            # I really wish python 2.4 supported except and finally together
            sync_end_timestamp = _now_timestamp()

            # Reload the importer in case the plugin edits the scratchpad
            repo_importer = importer_coll.find_one({'repo_id' : repo_id})
            repo_importer['last_sync'] = sync_end_timestamp
            importer_coll.save(repo_importer, safe=True)

            # Add a sync history entry for this run
            result = RepoSyncResult.error_result(repo_id, repo_importer['id'], repo_importer['importer_type_id'],
                                                 sync_start_timestamp, sync_end_timestamp, e, sys.exc_info()[2])
            sync_result_coll.save(result, safe=True)

            _LOG.exception(_('Exception caught from plugin during sync for repo [%(r)s]' % {'r' : repo_id}))
            raise PulpExecutionException(), None, sys.exc_info()[2]

        sync_end_timestamp = _now_timestamp()

        # Reload the importer in case the plugin edits the scratchpad
        repo_importer = importer_coll.find_one({'repo_id' : repo_id})
        repo_importer['last_sync'] = sync_end_timestamp
        importer_coll.save(repo_importer, safe=True)

        # Add a sync history entry for this run. Need to be safe here in case
        # the plugin is incorrect in its return
        if sync_report is not None and isinstance(sync_report, SyncReport):
            added_count = sync_report.added_count
            updated_count = sync_report.updated_count
            removed_count = sync_report.removed_count
            summary = sync_report.summary
            details = sync_report.details
            if sync_report.success_flag:
                result_code = RepoSyncResult.RESULT_SUCCESS
            else:
                result_code = RepoSyncResult.RESULT_FAILED
        else:
            _LOG.warn('Plugin type [%s] on repo [%s] did not return a valid sync report' % (repo_importer['importer_type_id'], repo_id))

            added_count = updated_count = removed_count = -1
            summary = details = _('Unknown')
            result_code = RepoSyncResult.RESULT_SUCCESS

        result = RepoSyncResult.expected_result(repo_id, repo_importer['id'], repo_importer['importer_type_id'],
                                               sync_start_timestamp, sync_end_timestamp, added_count, updated_count,
                                               removed_count, summary, details, result_code)
        sync_result_coll.save(result, safe=True)

        if result_code == RepoSyncResult.RESULT_FAILED:
            raise PulpExecutionException(_('Importer indicated a failed response'))

        # Request any auto-distributors publish (if we're here, the sync was successful)
        publish_manager = manager_factory.get_manager(manager_factory.TYPE_REPO_PUBLISH)
        try:
            sync_progress_report = conduit.progress_report
            publish_manager.auto_publish_for_repo(repo_id, sync_progress_report)
        except Exception:
            _LOG.exception('Exception automatically publishing distributors for repo [%s]' % repo_id)
            raise

    def get_repo_storage_directory(self, repo_id):
        """
        Returns the directory in which repositories can be stored as they are
        synchronized. The directory will be created if it does not exist.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @return: full path to the directory in which an importer can store the
                 given repository as it is synchronized
        @rtype:  str
        """

        dir = os.path.join(REPO_STORAGE_DIR, repo_id)
        if not os.path.exists(dir):
            os.makedirs(dir)

        return dir

    def sync_history(self, repo_id, limit=None):
        """
        Returns sync history entries for the given repo, sorted from most recent
        to oldest. If there are no entries, an empty list is returned.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param limit: maximum number of results to return
        @type  limit: int

        @return: list of sync history result instances
        @rtype:  list of L{pulp.server.db.model.repository.RepoSyncResult}

        @raise MissingResource: if repo_id does not reference a valid repo
        """

        # Validation
        repo = Repo.get_collection().find_one({'id' : repo_id})
        if repo is None:
            raise MissingResource(repo_id)

        if limit is None:
            limit = 10 # default here for each of REST API calls into here

        # Retrieve the entries
        cursor = RepoSyncResult.get_collection().find({'repo_id' : repo_id})
        cursor.limit(limit)
        cursor.sort('completed', pymongo.DESCENDING)

        return list(cursor)

def _now_timestamp():
    """
    @return: timestamp suitable for indicating when a sync completed
    @rtype:  str
    """
    now = datetime.datetime.now(dateutils.local_tz())
    now_in_iso_format = dateutils.format_iso8601_datetime(now)
    return now_in_iso_format