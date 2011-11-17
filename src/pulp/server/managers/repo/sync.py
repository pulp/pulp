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
import sys

# Pulp
from pulp.common import dateutils
import pulp.server.constants as pulp_constants
import pulp.server.content.loader as plugin_loader
from pulp.server.content.conduits.repo_sync import RepoSyncConduit
from pulp.server.content.plugins.config import PluginCallConfiguration
from pulp.server.db.model.gc_repository import Repo, RepoImporter
import pulp.server.managers.factory as manager_factory
import pulp.server.managers.repo._common as common_utils
from pulp.server.managers.repo._exceptions import MissingRepo, RepoSyncException, NoImporter, MissingImporterPlugin, SyncInProgress

# -- constants ----------------------------------------------------------------

REPO_STORAGE_DIR = os.path.join(pulp_constants.LOCAL_STORAGE, 'repos')

_LOG = logging.getLogger(__name__)

# -- manager ------------------------------------------------------------------

class RepoSyncManager:
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

        @raises MissingRepo: if repo_id does not refer to a valid repo
        @raises NoImporter: if the given repo does not have an importer set
        """

        repo_coll = Repo.get_collection()
        importer_coll = RepoImporter.get_collection()

        # Validation
        repo = repo_coll.find_one({'id' : repo_id})
        if repo is None:
            raise MissingRepo(repo_id)

        repo_importers = list(importer_coll.find({'repo_id' : repo_id}))

        if len(repo_importers) is 0:
            raise NoImporter(repo_id)
        repo_importer = repo_importers[0]

        if repo_importer['sync_in_progress']:
            raise SyncInProgress(repo_id)

        try:
            importer_instance, plugin_config = plugin_loader.get_importer_by_id(repo_importer['importer_type_id'])
        except plugin_loader.PluginNotFound:
            raise MissingImporterPlugin(repo_id), None, sys.exc_info()[2]

        # Assemble the data needed for the sync
        association_manager = manager_factory.repo_unit_association_manager()
        repo_manager = manager_factory.repo_manager()
        content_manager = manager_factory.content_manager()
        content_query_manager = manager_factory.content_query_manager()
        conduit = RepoSyncConduit(repo_id, repo_manager, self, association_manager,
                                  content_manager, content_query_manager)

        call_config = PluginCallConfiguration(plugin_config, repo_importer['config'], sync_config_override)
        transfer_repo = common_utils.to_transfer_repo(repo)
        transfer_repo.working_dir = common_utils.importer_working_dir(repo_importer['importer_type_id'], repo_id, mkdir=True)

        # Perform the sync
        try:
            repo_importer['sync_in_progress'] = True
            importer_coll.save(repo_importer, safe=True)
            importer_instance.sync_repo(transfer_repo, conduit, call_config)
        except Exception:
            # I really wish python 2.4 supported except and finally together

            # Reload the importer in case the plugin edits the scratchpad
            repo_importer = importer_coll.find_one({'repo_id' : repo_id})
            repo_importer['sync_in_progress'] = False
            repo_importer['last_sync'] = _sync_finished_timestamp()
            importer_coll.save(repo_importer, safe=True)

            _LOG.exception(_('Exception caught from plugin during sync for repo [%(r)s]' % {'r' : repo_id}))
            raise RepoSyncException(repo_id), None, sys.exc_info()[2]

        # Reload the importer in case the plugin edits the scratchpad
        repo_importer = importer_coll.find_one({'repo_id' : repo_id})
        repo_importer['sync_in_progress'] = False
        repo_importer['last_sync'] = _sync_finished_timestamp()
        importer_coll.save(repo_importer, safe=True)

        # Request any auto-distributors publish (if we're here, the sync was successful)
        publish_manager = manager_factory.get_manager(manager_factory.TYPE_REPO_PUBLISH)
        try:
            publish_manager.auto_publish_for_repo(repo_id)
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

def _sync_finished_timestamp():
    """
    @return: timestamp suitable for indicating when a sync completed
    @rtype:  str
    """
    now = datetime.datetime.now(dateutils.local_tz())
    now_in_iso_format = dateutils.format_iso8601_datetime(now)
    return now_in_iso_format