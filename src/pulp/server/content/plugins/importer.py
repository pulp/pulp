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

    def validate_config(self, repo_data, repo_config):
        """
        Allows the importer to check the contents of a potential configuration
        for the given repository. This call is made both for the addition of
        this importer to a new repository as well as updating the configuration
        for this importer on a previously configured repository. The implementation
        should use the given repository data to ensure that updating the
        configuration does not put the repository into an inconsistent state.

        @param repo_data: metadata describing the repository to which the
                          configuration applies
        @type  repo_data: dict

        @param repo_config: proposed configuration used by this importer for
                                the given repo
        @type  repo_config: dict

        @return: True if the configuration is valid; False otherwise
        @rtype:  bool
        """
        raise NotImplementedError()

    def sync_repo(self, repo_data, sync_conduit, importer_config=None, repo_config=None):
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
