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


class Importer(object):
    """
    Base class for importer plugin development.
    """

    @classmethod
    def metadata(cls):
        return {}

    def sync(self, repo_data, sync_conduit, importer_config=None, repo_config=None):
        """
        Sync content into a repository.
        @param repo_data: metadata that describes a pulp repository
        @type repo_data: dict
        @param sync_conduit: api instance that provides limited pulp functionality
        @type sync_conduit: L{ContentPluginHook} instance
        @param importer_config: configuration for the importer instance
        @type importer_config: None or dict
        @param repo_config: configuration for a specific repo
        @type repo_config: None or dict
        """
        raise NotImplementedError()

    def pre_import_unit(self, repo_data, unit_data, importer_config=None, repo_config=None):
        """
        Optional content unit pre-processing before it is imported into a
        repository.
        @param repo_data: metadata that describes a pulp repository
        @type repo_data: dict
        @param unit_data: metadata that describes a content unit
        @type unit_data: dict
        @param importer_config: configuration for the importer instance
        @type importer_config: None or dict
        @param repo_config: configuration for a specific repo
        @type repo_config: None or dict
        """
        pass

    def import_unit(self, repo_data, unit_data, temp_location, importer_config=None, repo_config=None):
        """
        Import a unit of content into a repository.
        @param repo_data: metadata that describes a pulp repository
        @type repo_data: dict
        @param unit_data: metadata that describes a content unit
        @type unit_data: dict
        @param temp_location: full path to content unit on disk
        @type temp_location: str
        @param importer_config: configuration for the importer instance
        @type importer_config: None or dict
        @param repo_config: configuration for a specific repo
        @type repo_config: None or dict
        """
        raise NotImplementedError()

    def delete_repo(self, repo_data, delete_conduit, importer_config=None, repo_config=None):
        """
        Delete a repository and its content.
        @param repo_data: metadata that describes a pulp repository
        @type repo_data: dict
        @param delete_conduit: api instance that provides limited pulp functionality
        @type delete_conduit: L{ContentPluginHook} instance
        @param importer_config: configuration for the importer instance
        @type importer_config: None or dict
        @param repo_config: configuration for a specific repo
        @type repo_config: None or dict
        """
        raise NotImplementedError()

    def clone_repo(self, repo_data, clone_data, clone_conduit, importer_config=None, repo_config=None):
        """
        Clone a repository.
        @param repo_data: metadata that describes a pulp repository
        @type repo_data: dict
        @param clone_data: metadata that describes a pulp repository
        @type clone_data: dict
        @param clone_conduit: api instance that provides limited pulp functionality
        @type clone_conduit: L{ContentPluginHook} instance
        @param importer_config: configuration for the importer instance
        @type importer_config: None or dict
        @param repo_config: configuration for a specific repo
        @type repo_config: None or dict
        """
        raise NotImplementedError()
