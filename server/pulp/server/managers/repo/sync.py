# -*- coding: utf-8 -*-
#
# Copyright © 2011-2013 Red Hat, Inc.
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

import datetime
import isodate
import logging
import os
import sys
from gettext import gettext as _

from celery import task

from pulp.common import dateutils, constants
from pulp.plugins.loader import api as plugin_api
from pulp.plugins.loader import exceptions as plugin_exceptions
from pulp.plugins.conduits.repo_sync import RepoSyncConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.model import SyncReport
from pulp.server import config as pulp_config
from pulp.server.async.tasks import register_sigterm_handler, Task
from pulp.server.db.model.repository import Repo, RepoContentUnit, RepoImporter, RepoSyncResult
from pulp.server.exceptions import MissingResource, PulpExecutionException, InvalidValue
from pulp.server.managers import factory as manager_factory
from pulp.server.managers.repo import _common as common_utils


logger = logging.getLogger(__name__)


class RepoSyncManager(object):
    """
    Manager used to handle sync and sync query operations.
    """
    @staticmethod
    def sync(repo_id, sync_config_override=None):
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

        @return: The synchronization report.
        @rtype: L{pulp.server.plugins.model.SyncReport}

        @raise MissingResource: if repo_id does not refer to a valid repo
        @raise OperationFailed: if the given repo does not have an importer set
        """

        repo_coll = Repo.get_collection()

        # Validation
        repo = repo_coll.find_one({'id' : repo_id})
        if repo is None:
            raise MissingResource(repo_id)

        importer_instance, importer_config = RepoSyncManager._get_importer_instance_and_config(
            repo_id)

        if importer_instance is None:
            raise MissingResource(repo_id)

        importer_manager = manager_factory.repo_importer_manager()
        repo_importer = importer_manager.get_importer(repo_id)

        # Assemble the data needed for the sync
        conduit = RepoSyncConduit(repo_id, repo_importer['id'], RepoContentUnit.OWNER_TYPE_IMPORTER,
                                  repo_importer['id'])

        call_config = PluginCallConfiguration(importer_config, repo_importer['config'],
                                              sync_config_override)
        transfer_repo = common_utils.to_transfer_repo(repo)
        transfer_repo.working_dir = common_utils.importer_working_dir(
            repo_importer['importer_type_id'], repo_id, mkdir=True)

        # Fire an events around the call
        fire_manager = manager_factory.event_fire_manager()
        fire_manager.fire_repo_sync_started(repo_id)
        sync_result = RepoSyncManager._do_sync(repo, importer_instance, transfer_repo, conduit,
                                               call_config)
        fire_manager.fire_repo_sync_finished(sync_result)

        if sync_result['result'] == RepoSyncResult.RESULT_FAILED:
            raise PulpExecutionException(_('Importer indicated a failed response'))

        return sync_result

        # auto publish call has been moved to a dependent call in a multiple
        # call execution through the coordinator

    @staticmethod
    def _get_importer_instance_and_config(repo_id):
        importer_manager = manager_factory.repo_importer_manager()
        try:
            repo_importer = importer_manager.get_importer(repo_id)
            importer, config = plugin_api.get_importer_by_id(repo_importer['importer_type_id'])
        except (MissingResource, plugin_exceptions.PluginNotFound):
            importer = None
            config = None
        return importer, config

    @staticmethod
    def _do_sync(repo, importer_instance, transfer_repo, conduit, call_config):
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
        repo_importer = importer_coll.find_one({'repo_id' : repo_id})

        # Perform the sync
        sync_start_timestamp = _now_timestamp()
        sync_end_timestamp = None
        result = None

        try:
            # Replace the Importer's sync_repo() method with our register_sigterm_handler decorator,
            # which will set up cancel_sync_repo() as the target for the signal handler
            sync_repo = register_sigterm_handler(importer_instance.sync_repo,
                                                 importer_instance.cancel_sync_repo)
            sync_report = sync_repo(transfer_repo, conduit, call_config)

        except Exception, e:
            sync_end_timestamp = _now_timestamp()

            result = RepoSyncResult.error_result(
                repo_id, repo_importer['id'], repo_importer['importer_type_id'],
                sync_start_timestamp, sync_end_timestamp, e, sys.exc_info()[2])

            logger.exception(
                _('Exception caught from plugin during sync for repo [%(r)s]' % {'r' : repo_id}))
            raise

        else:
            sync_end_timestamp = _now_timestamp()

            # Need to be safe here in case the plugin is incorrect in its return
            if isinstance(sync_report, SyncReport):

                added_count = sync_report.added_count
                updated_count = sync_report.updated_count
                removed_count = sync_report.removed_count
                summary = sync_report.summary
                details = sync_report.details

                if sync_report.canceled_flag:
                    result_code = RepoSyncResult.RESULT_CANCELED

                elif sync_report.success_flag:
                    result_code = RepoSyncResult.RESULT_SUCCESS

                else:
                    result_code = RepoSyncResult.RESULT_FAILED

            else:
                msg = _('Plugin type [%s] on repo [%s] did not return a valid sync report')
                msg = msg % (repo_importer['importer_type_id'], repo_id)
                logger.warn(msg)

                added_count = updated_count = removed_count = -1 # None?
                summary = details = msg
                result_code = RepoSyncResult.RESULT_ERROR # RESULT_UNKNOWN?

            result = RepoSyncResult.expected_result(
                repo_id, repo_importer['id'], repo_importer['importer_type_id'],
                sync_start_timestamp, sync_end_timestamp, added_count, updated_count, removed_count,
                summary, details, result_code)

        finally:
            # Do an update instead of a save in case the importer has changed the scratchpad
            importer_coll.update({'repo_id': repo_id}, {'$set': {'last_sync': sync_end_timestamp}},
                                 safe=True)
            # Add a sync history entry for this run
            sync_result_coll.save(result, safe=True)

        return result

    def sync_history(self, repo_id, limit=None, sort=constants.SORT_DESCENDING, start_date=None,
                     end_date=None):
        """
        Returns sync history entries for the given repo, sorted from most recent
        to oldest. If there are no entries, an empty list is returned.

        :param repo_id:     identifies the repo
        :type  repo_id:     str
        :param limit:       if specified, the query will only return up to this amount of
                            entries; default is to return the entire sync history
        :type  limit:       int
        :param sort:        Indicates the sort direction of the results, which are sorted by start date. Options
                            are "ascending" and "descending". Descending is the default.
        :type  sort:        str
        :param start_date:  if specified, no events prior to this date will be returned. Expected to be an
                            iso8601 datetime string.
        :type  start_date:  str
        :param end_date:    if specified, no events after this date will be returned. Expected to be an
                            iso8601 datetime string.
        :type end_date:     str

        :return: list of sync history result instances
        :rtype:  list

        :raise MissingResource: if repo_id does not reference a valid repo
        :raise InvalidValue: if one or more options are invalid
        """

        # Validation
        repo = Repo.get_collection().find_one({'id': repo_id})
        if repo is None:
            raise MissingResource(repo_id)

        invalid_values = []
        # Verify the limit makes sense
        if limit is not None:
            try:
                limit = int(limit)
                if limit < 1:
                    invalid_values.append('limit')
            except ValueError:
                invalid_values.append('limit')

        # Verify the sort direction is valid
        if sort not in constants.SORT_DIRECTION:
            invalid_values.append('sort')

        # Verify that start_date and end_date is valid
        if start_date is not None:
            try:
                dateutils.parse_iso8601_datetime(start_date)
            except (ValueError, isodate.ISO8601Error):
                invalid_values.append('start_date')
        if end_date is not None:
            try:
                dateutils.parse_iso8601_datetime(end_date)
            except (ValueError, isodate.ISO8601Error):
                invalid_values.append('end_date')

        # Report any invalid values
        if invalid_values:
            raise InvalidValue(invalid_values)

        # Assemble the mongo search parameters
        search_params = {'repo_id': repo_id}
        # Add in date range limits if specified
        date_range = {}
        if start_date:
            date_range['$gte'] = start_date
        if end_date:
            date_range['$lte'] = end_date
        if len(date_range) > 0:
            search_params['started'] = date_range

        # Retrieve the entries
        cursor = RepoSyncResult.get_collection().find(search_params)
        # Sort the results on the 'started' field. By default, descending order is used
        cursor.sort('started', direction=constants.SORT_DIRECTION[sort])
        if limit is not None:
            cursor.limit(limit)

        return list(cursor)

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


sync = task(RepoSyncManager.sync, base=Task)


def _now_timestamp():
    """
    @return: iso 8601 UTC timestamp suitable for indicating when a sync completed
    @rtype:  str
    """
    now = dateutils.now_utc_datetime_with_tzinfo()
    now_in_iso_format = dateutils.format_iso8601_datetime(now)
    return now_in_iso_format


def _repo_storage_dir():
    storage_dir = pulp_config.config.get('server', 'storage_dir')
    dir = os.path.join(storage_dir, 'repos')
    return dir
