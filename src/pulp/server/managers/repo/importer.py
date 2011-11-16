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

from pulp.server.db.model.gc_repository import Repo, RepoImporter
import pulp.server.content.loader as plugin_loader
from pulp.server.content.plugins.config import PluginCallConfiguration
import pulp.server.managers.repo._common as common_utils
from pulp.server.managers.repo._exceptions import MissingRepo, MissingImporter, InvalidImporterType, InvalidImporterConfiguration, ImporterInitializationException

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- manager ------------------------------------------------------------------

class RepoImporterManager:

    def get_importer(self, repo_id):
        pass

    def set_importer(self, repo_id, importer_type_id, repo_plugin_config):
        """
        Configures an importer to be used for the given repository.

        Keep in mind this method is written assuming single importer for a repo.
        The domain model technically supports multiple importers, but this
        call is what enforces the single importer behavior.

        @param repo_id: identifies the repo
        @type  repo_id; str

        @param importer_type_id: identifies the type of importer being added;
                                 must correspond to an importer loaded at server startup
        @type  importer_type_id: str

        @param repo_plugin_config: configuration values for the importer; may be None
        @type  repo_plugin_config: dict

        @raises MissingRepo: if repo_id does not represent a valid repo
        @raises InvalidImporterType: if there is no importer with importer_type_id
        @raises InvalidImporterConfiguration: if the importer cannot be initialized
                for the given repo
        @raises ImporterInitializationException: if the plugin raises an error
                during initialization
        """

        repo_coll = Repo.get_collection()
        importer_coll = RepoImporter.get_collection()

        # Validation
        repo = repo_coll.find_one({'id' : repo_id})
        if repo is None:
            raise MissingRepo(repo_id)

        if not plugin_loader.is_valid_importer(importer_type_id):
            raise InvalidImporterType(importer_type_id)

        importer_instance, plugin_config = plugin_loader.get_importer_by_id(importer_type_id)

        # Let the importer plugin verify the configuration
        call_config = PluginCallConfiguration(plugin_config, repo_plugin_config)
        transfer_repo = common_utils.to_transfer_repo(repo)
        transfer_repo.working_dir = common_utils.importer_working_dir(importer_type_id, repo_id)

        try:
            valid_config = importer_instance.validate_config(transfer_repo, call_config)
        except Exception:
            _LOG.exception('Exception received from importer [%s] while validating config' % importer_type_id)
            raise InvalidImporterConfiguration, None, sys.exc_info()[2]

        if not valid_config:
            raise InvalidImporterConfiguration()

        # Remove old importer if one exists
        try:
            self.remove_importer(repo_id)
        except MissingImporter:
            pass # it didn't exist, so no harm done

        # Let the importer plugin initialize the repository
        try:
            importer_instance.importer_added(transfer_repo, call_config)
        except Exception:
            _LOG.exception('Error initializing importer [%s] for repo [%s]' % (importer_type_id, repo_id))
            raise ImporterInitializationException(), None, sys.exc_info()[2]

        # Database Update
        importer_id = importer_type_id # use the importer name as its repo ID

        importer = RepoImporter(repo_id, importer_id, importer_type_id, repo_plugin_config)
        importer_coll.save(importer, safe=True)

        return importer

    def remove_importer(self, repo_id):
        """
        Removes an importer from a repository.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @raises MissingRepo: if the given repo does not exist
        @raises MissingImporter: if the given repo does not have an importer
        """

        repo_coll = Repo.get_collection()
        importer_coll = RepoImporter.get_collection()

        # Validation
        repo = repo_coll.find_one({'id' : repo_id})
        if repo is None:
            raise MissingRepo(repo_id)

        repo_importer = importer_coll.find_one({'repo_id' : repo_id})

        if repo_importer is None:
            raise MissingImporter()

        # Call the importer's cleanup method
        importer_type_id = repo_importer['importer_type_id']
        importer_instance, plugin_config = plugin_loader.get_importer_by_id(importer_type_id)

        call_config = PluginCallConfiguration(plugin_config, repo_importer['config'])

        transfer_repo = common_utils.to_transfer_repo(repo)
        transfer_repo.working_dir = common_utils.importer_working_dir(importer_type_id, repo_id)

        importer_instance.importer_removed(transfer_repo, call_config)

        # Update the database to reflect the removal
        importer_coll.remove({'repo_id' : repo_id}, safe=True)

    def update_importer_config(self, repo_id, importer_config):
        """
        Attempts to update the saved configuration for the given repo's importer.
        The importer will be asked if the new configuration is valid. If not,
        this method will raise an error and the existing configuration will
        remain unchanged.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param importer_config: new configuration values to use for this repo
        @type  importer_config: dict

        @raises MissingRepo: if the given repo does not exist
        @raises MissingImporter: if the given repo does not have an importer
        @raises InvalidImporterConfiguration: if the plugin indicates the given
                configuration is invalid
        """

        repo_coll = Repo.get_collection()
        importer_coll = RepoImporter.get_collection()

        # Input Validation
        repo = repo_coll.find_one({'id' : repo_id})
        if repo is None:
            raise MissingRepo(repo_id)

        repo_importer = importer_coll.find_one({'repo_id' : repo_id})
        if repo_importer is None:
            raise MissingImporter()

        importer_type_id = repo_importer['importer_type_id']
        importer_instance, plugin_config = plugin_loader.get_importer_by_id(importer_type_id)

        # Let the importer plugin verify the configuration
        call_config = PluginCallConfiguration(plugin_config, importer_config)
        transfer_repo = common_utils.to_transfer_repo(repo)
        transfer_repo.working_dir = common_utils.importer_working_dir(importer_type_id, repo_id)

        try:
            valid_config = importer_instance.validate_config(transfer_repo, call_config)
        except Exception:
            _LOG.exception('Exception received from importer [%s] while validating config for repo [%s]' % (importer_type_id, repo_id))
            raise InvalidImporterConfiguration, None, sys.exc_info()[2]

        if not valid_config:
            raise InvalidImporterConfiguration()

        # If we got this far, the new config is valid, so update the database
        repo_importer['config'] = importer_config
        importer_coll.save(repo_importer, safe=True)

    def get_importer_scratchpad(self, repo_id):
        """
        Returns the contents of the importer's scratchpad for the given repo.
        If there is no importer or the scratchpad has not been set, None is
        returned.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @return: value set for the importer's scratchpad
        @rtype:  anything that can be saved in the database
        """

        importer_coll = RepoImporter.get_collection()

        # Validation
        repo_importer = importer_coll.find_one({'repo_id' : repo_id})
        if repo_importer is None:
            return None

        scratchpad = repo_importer.get('scratchpad', None)
        return scratchpad

    def set_importer_scratchpad(self, repo_id, contents):
        """
        Sets the value of the scratchpad for the given repo and saves it to
        the database. If there is a previously saved value it will be replaced.

        If the repo has no importer associated with it, this call does nothing.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param contents: value to write to the scratchpad field
        @type  contents: anything that can be saved in the database
        """

        importer_coll = RepoImporter.get_collection()

        # Validation
        repo_importer = importer_coll.find_one({'repo_id' : repo_id})
        if repo_importer is None:
            return

        # Update
        repo_importer['scratchpad'] = contents
        importer_coll.save(repo_importer, safe=True)

