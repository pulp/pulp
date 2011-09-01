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

import copy
import datetime
from gettext import gettext as _
import logging
import sys

from pulp.common import dateutils
import pulp.server.content.manager as plugin_manager
from pulp.server.content.conduits.repo_sync import RepoSyncConduit
from pulp.server.db.model.gc_repository import Repo, RepoImporter
import pulp.server.managers.factory as manager_factory

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- exceptions ---------------------------------------------------------------

class RepoSyncException(Exception):
    """
    Raised when an error occurred during a repo sync. Subclass exceptions are
    used to further categorize the error encountered. The ID of the repository
    that caused the error is included in the exception.
    """
    def __init__(self, repo_id):
        Exception.__init__(self)
        self.repo_id = repo_id

    def __str__(self):
        return _('Exception [%(e)s] raised for repository [%(r)s]') % \
               {'e' : self.__class__.__name__, 'r' : self.repo_id}

class NoImporter(RepoSyncException):
    """
    Indicates a sync was requested on a repository that is not configured
    with an importer.
    """
    pass

class MissingRepo(RepoSyncException):
    """
    Indicates an operation was requested against a repo that doesn't exist.
    """
    pass

class MissingImporterPlugin(RepoSyncException):
    """
    Indicates a repo is configured with an importer type that could not be
    found in the plugin manager.
    """
    pass

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
        try:
            importer_instance, importer_config = plugin_manager.get_importer_by_name(repo_importer['importer_type_id'])
        except plugin_manager.PluginNotFound:
            raise MissingImporterPlugin(repo_id), None, sys.exc_info()[2]

        # Assemble the data needed for the sync
        association_manager = manager_factory.get_manager(manager_factory.TYPE_REPO_ASSOCIATION)
        conduit = RepoSyncConduit(repo_id, association_manager)

        # Take the repo's default sync config and merge in the override values
        # for this sync alone (don't store it back to the DB)
        sync_config = dict(repo_importer['config'])
        if sync_config_override is not None:
            sync_config.update(sync_config_override)

        # Perform the sync
        try:
            repo_importer['sync_in_progress'] = True
            importer_coll.save(repo_importer, safe=True)
            importer_instance.sync(repo, conduit, importer_config, sync_config)
        except Exception:
            # I really wish python 2.4 supported except and finally together
            repo_importer['sync_in_progress'] = False
            repo_importer['last_sync'] = _sync_finished_timestamp()
            importer_coll.save(repo_importer, safe=True)

            _LOG.exception(_('Exception caught from plugin during sync for repo [%(r)s]' % {'r' : repo_id}))
            raise RepoSyncException(repo_id)

        repo_importer['sync_in_progress'] = False
        repo_importer['last_sync'] = _sync_finished_timestamp()
        importer_coll.save(repo_importer, safe=True)

def _sync_finished_timestamp():
    """
    @return: timestamp suitable for indicating when a sync completed.
    @rtype:  str
    """
    now = datetime.datetime.now(dateutils.local_tz())
    now_in_iso_format = dateutils.format_iso8601_datetime(now)
    return now_in_iso_format