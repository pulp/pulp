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

from pulp.server.content.plugin.base import ContentPlugin, config_override


class Importer(ContentPlugin):
    """
    Base class for importer plugin development.
    """

    def __init__(self, config):
        super(Importer, self).__init__(config)

    @config_override
    def sync(self, repo_data, sync_hook, config=None, options=None):
        """
        Sync content into a repository.
        @param repo_data: metadata that describes a pulp repository
        @type repo_data: dict
        @param sync_hook: api instance that provides limited pulp functionality
        @type sync_hook: L{ContentPluginHook} instance
        @param config: configuration override for importer instance
        @type config: None or dict
        @param options: individual sync call options
        @type options: None or dict
        """
        raise NotImplementedError()

    @config_override
    def pre_import_unit(self, repo_data, unit_data, config=None, options=None):
        """
        Optional content unit pre-processing before it is imported into a
        repository.
        @param repo_data: metadata that describes a pulp repository
        @type repo_data: dict
        @param unit_data: metadata that describes a content unit
        @type unit_data: dict
        @param temp_location: full path to content unit on disk
        @type temp_location: str
        @param config: configuration override for importer instance
        @type options: None or dict
        @param options: individual pre_import_unit call options
        @type options: None or dict
        """
        pass

    @config_override
    def import_unit(self, repo_data, unit_data, temp_location, config=None, options=None):
        """
        Import a unit of content into a repository.
        @param repo_data: metadata that describes a pulp repository
        @type repo_data: dict
        @param unit_data: metadata that describes a content unit
        @type unit_data: dict
        @param temp_location: full path to content unit on disk
        @type temp_location: str
        @param config: configuration override for importer instance
        @type config: None or dict
        @param options: individual import_unit call options
        @type options: None or dict
        """
        raise NotImplementedError()

    @config_override
    def delete_repo(self, repo_data, delete_hook, config=None, options=None):
        """
        Delete a repository and its content.
        @param repo_data: metadata that describes a pulp repository
        @type repo_data: dict
        @param delete_hook: api instance that provides limited pulp functionality
        @type delete_hook: L{ContentPluginHook} instance
        @param config: configuration override for importer instance
        @type config: None or dict
        @param options: individual import_unit call options
        @type options: None or dict
        """
        raise NotImplementedError()

    @config_override
    def clone_repo(self, repo_data, clone_data, clone_hook, config=None, options=None):
        """
        Clone a repository.
        @param repo_data: metadata that describes a pulp repository
        @type repo_data: dict
        @param clone_data: metadata that describes a pulp repository
        @type clone_data: dict
        @param clone_hook: api instance that provides limited pulp functionality
        @type clone_hook: L{ContentPluginHook} instance
        @param config: configuration override for importer instance
        @type config: None or dict
        @param options: individual import_unit call options
        @type options: None or dict
        """
        raise NotImplementedError()
