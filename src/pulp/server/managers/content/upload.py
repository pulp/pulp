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

import logging
import sys

from   pulp.server.content.conduits.repo_sync import RepoSyncConduit
import pulp.server.content.loader as content_loader
from   pulp.server.content.plugins.config import PluginCallConfiguration
from   pulp.server.exceptions import PulpDataException, MissingResource, PulpExecutionException
import pulp.server.managers.factory as manager_factory
import pulp.server.managers.repo._common as repo_common_utils

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- manager ------------------------------------------------------------------

class ContentUploadManager(object):

    def is_valid_upload(self, repo_id, unit_type_id):
        """
        Checks that the repository is configured to handle an upload request
        for the given unit type ID. This should be called prior to beginning
        the upload to prevent a wasted effort in the bits uploading.

        @param repo_id: identifies the repo into which the unit is being uploaded
        @param unit_type_id: type of unit being uploaded

        @return: true if the repository can attempt to handle the unit
        @rtype:  bool

        @raise MissingResource: if the repository or its importer do not exist
        """

        importer_manager = manager_factory.repo_importer_manager()

        # Will raise an appropriate exception if it cannot be found
        repo_importer = importer_manager.get_importer(repo_id)

        # Make sure the importer on the repo can support the indicated type
        importer_types = content_loader.list_importer_types(repo_importer['importer_type_id'])['types']

        if unit_type_id not in importer_types:
            raise PulpDataException('Invalid unit type for repository')

        return True

    def import_uploaded_unit(self, repo_id, unit_type_id, unit_key, unit_metadata, file_path):
        """
        Called to trigger the importer's handling of an uploaded unit. This
        should not be called until the bits have finished uploading. The
        importer is then responsible for moving the file to the correct location,
        adding it to the Pulp server's inventory, and associating it with the
        repository.

        This call will first call is_valid_upload to check the integrity of the
        destination repository. See that method's documentation for exception
        possibilities.

        @param repo_id: identifies the repository into which the unit is uploaded
        @type  repo_id: str

        @param unit_type_id: type of unit being uploaded
        @type  unit_type_id: str

        @param unit_key: unique identifier for the unit (user-specified)
        @type  unit_key: dict

        @param unit_metadata: any user-specified information about the unit
        @type  unit_metadata: dict

        @param file_path: path to the location on the server's filesystem where
               the uploaded file is stored; may be None in the event a unit is
               purely defined by metadata
        @type  file_path: str
        """

        # If it doesn't raise an exception, it's good to go
        self.is_valid_upload(repo_id, unit_type_id)

        repo_query_manager = manager_factory.repo_query_manager()
        importer_manager = manager_factory.repo_importer_manager()

        repo = repo_query_manager.find_by_id(repo_id)
        repo_importer = importer_manager.get_importer(repo_id)

        try:
            importer_instance, plugin_config = content_loader.get_importer_by_id(repo_importer['importer_type_id'])
        except content_loader.PluginNotFound:
            raise MissingResource(repo_id), None, sys.exc_info()[2]

        # Assemble the data needed for the sync
        conduit = RepoSyncConduit(repo_id, repo_importer['id'])

        call_config = PluginCallConfiguration(plugin_config, repo_importer['config'], None)
        transfer_repo = repo_common_utils.to_transfer_repo(repo)
        transfer_repo.working_dir = repo_common_utils.importer_working_dir(repo_importer['importer_type_id'], repo_id, mkdir=True)

        # Invoke the importer
        try:
            # def upload_unit(self, type_id, unit_key, metadata, file_path, conduit, config):
            report = importer_instance.upload_unit(unit_type_id, unit_key, unit_metadata, file_path, conduit, call_config)
        except Exception, e:
            _LOG.exception('Error from the importer while importing uploaded unit to repository [%s]' % repo_id)
            raise PulpExecutionException(e), None, sys.exc_info()[2]

        # TODO: Add support for tracking the report as a history entry on the repo
        return report