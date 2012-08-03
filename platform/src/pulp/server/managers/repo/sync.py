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
from pulp.server import config as pulp_config
from pulp.plugins.loader import api as plugin_api
from pulp.plugins.loader import exceptions as plugin_exceptions
from pulp.plugins.conduits.repo_sync import RepoSyncConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import SyncReport
from pulp.server.db.model.repository import Repo, RepoContentUnit, RepoImporter, RepoSyncResult
from pulp.server.dispatch import constants as dispatch_constants
from pulp.server.exceptions import MissingResource, PulpExecutionException
from pulp.server.managers import factory as manager_factory
from pulp.server.managers.repo import _common as common_utils


# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- manager ------------------------------------------------------------------

class RepoSyncManager(object):
    """
    Manager used to handle sync and sync query operations.
    """

    def prep_sync(self, call_request, call_report):
        """
        Task enqueue callback that sets the keyword argument of the importer
        instance to use for the sync.
        @param call_request: call request for repo sync
        @param call_report: call report for repo sync
        """
        assert call_report.state in dispatch_constants.CALL_READY_STATES

        repo_id = call_request.args[0] # XXX this will fail if we start setting
                                       # the repo_id as a keyword argument
                                       # jconnor (2012-07-30)

        importer, config = self._get_importer_instance_and_config(repo_id)

        call_request.kwargs['importer_instance'] = importer
        call_request.kwargs['importer_config'] = config

        if importer is not None:
            call_request.add_control_hook(dispatch_constants.CALL_CANCEL_CONTROL_HOOK, importer.cancel_sync_repo)

    def _get_importer_instance_and_config(self, repo_id):
        importer_manager = manager_factory.repo_importer_manager()
        try:
            repo_importer = importer_manager.get_importer(repo_id)
            importer, config = plugin_api.get_importer_by_id(repo_importer['importer_type_id'])
        except (MissingResource, plugin_exceptions.PluginNotFound):
            importer = None
            config = None
        return importer, config

    def sync(self, repo_id, importer_instance=None, importer_config=None, sync_config_override=None):
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

        @param importer_instance: the importer instance for this repo and this sync
        @type importer_instance: pulp.plugins.importer.Importer

        @param importer_config: base configuration for the importer
        @type importer_config: dict

        @param sync_config_override: optional config containing values to use
                                     for this sync only
        @type  sync_config_override: dict

        @raise MissingResource: if repo_id does not refer to a valid repo
        @raise OperationFailed: if the given repo does not have an importer set
        """

        repo_coll = Repo.get_collection()

        # Validation
        repo = repo_coll.find_one({'id' : repo_id})
        if repo is None:
            raise MissingResource(repo_id)

        if importer_instance is None:
            raise MissingResource(repo_id)

        importer_manager = manager_factory.repo_importer_manager()
        repo_importer = importer_manager.get_importer(repo_id)

        # Assemble the data needed for the sync
        conduit = RepoSyncConduit(repo_id, repo_importer['id'], RepoContentUnit.OWNER_TYPE_IMPORTER, repo_importer['id'])

        call_config = PluginCallConfiguration(importer_config, repo_importer['config'], sync_config_override)
        transfer_repo = common_utils.to_transfer_repo(repo)
        transfer_repo.working_dir = common_utils.importer_working_dir(repo_importer['importer_type_id'], repo_id, mkdir=True)

        # Fire an events around the call
        fire_manager = manager_factory.event_fire_manager()
        fire_manager.fire_repo_sync_started(repo_id)
        sync_result = self._do_sync(repo, importer_instance, transfer_repo, conduit, call_config)
        fire_manager.fire_repo_sync_finished(sync_result)

        if sync_result['result'] == RepoSyncResult.RESULT_FAILED:
            raise PulpExecutionException(_('Importer indicated a failed response'))

        # auto publish call has been moved to a dependent call in a multiple
        # call execution through the coordinator

    def _do_sync(self, repo, importer_instance, transfer_repo, conduit, call_config):
        """
        Once all of the preparation for a sync has taken place, this call
        will perform the sync, making the necessary database updates. It returns
        the sync result instance (already saved to the database). This call
        does not have any behavior based on the success/failure of the sync;
        it is up to the caller to raise an exception in the event of a failed
        sync if that behavior is desired.
        """

        importer_coll = RepoImporter.get_collection()
        sync_result_coll = RepoSyncResult.get_collection()
        repo_id = repo['id']

        # Perform the sync
        sync_start_timestamp = _now_timestamp()
        try:
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
        return result

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

    # -- utility --------------------------------------------------------------

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

def _now_timestamp():
    """
    @return: timestamp suitable for indicating when a sync completed
    @rtype:  str
    """
    now = datetime.datetime.now(dateutils.local_tz())
    now_in_iso_format = dateutils.format_iso8601_datetime(now)
    return now_in_iso_format

def _repo_storage_dir():
    storage_dir = pulp_config.config.get('server', 'storage_dir')
    dir = os.path.join(storage_dir, 'repos')
    return dir
