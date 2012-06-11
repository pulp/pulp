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
import pulp.server.managers.factory as manager_factory
import pulp.server.managers.repo._common as common_utils
from pulp.server.exceptions import MissingResource, InvalidValue, PulpExecutionException, PulpDataException

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- manager ------------------------------------------------------------------

class RepoImporterManager(object):

    def get_importer(self, repo_id):
        """
        Returns metadata about an importer associated with the given repo.

        @return: key-value pairs describing the importer in use
        @rtype:  dict

        @raise MissingResource: if the repo does not exist or has no importer associated
        """

        importer = RepoImporter.get_collection().find_one({'repo_id' : repo_id})
        if importer is None:
            raise MissingResource(repo_id)

        return importer

    def get_importers(self, repo_id):
        """
        Returns a list of all importers associated with the given repo.

        @return: list of key-value pairs describing the importers in use; empty
                 list if the repo has no importers
        @rtype:  list of dict

        @raise MissingResource: if the given repo doesn't exist
        """

        repo = Repo.get_collection().find_one({'id' : repo_id})
        if repo is None:
            raise MissingResource(repo_id)

        importers = list(RepoImporter.get_collection().find({'repo_id' : repo_id}))
        return importers

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

        @raise MissingResource: if repo_id does not represent a valid repo
        @raise InvalidImporterConfiguration: if the importer cannot be
               initialized for the given repo
        """

        repo_coll = Repo.get_collection()
        importer_coll = RepoImporter.get_collection()

        # Validation
        repo = repo_coll.find_one({'id' : repo_id})
        if repo is None:
            raise MissingResource(repo_id)

        if not plugin_loader.is_valid_importer(importer_type_id):
            raise InvalidValue(['importer_type_id'])

        importer_instance, plugin_config = plugin_loader.get_importer_by_id(importer_type_id)

        # Convention is that a value of None means unset. Remove any keys that
        # are explicitly set to None so the plugin will default them.
        if repo_plugin_config is not None:
            clean_config = dict([(k, v) for k, v in repo_plugin_config.items() if v is not None])
        else:
            clean_config = None

        # Let the importer plugin verify the configuration
        call_config = PluginCallConfiguration(plugin_config, clean_config)
        transfer_repo = common_utils.to_transfer_repo(repo)
        transfer_repo.working_dir = common_utils.importer_working_dir(importer_type_id, repo_id)

        query_manager = manager_factory.repo_query_manager()
        related_repos = query_manager.find_with_importer_type(importer_type_id)

        transfer_related_repos = []
        for r in related_repos:
            all_configs = [d['config'] for d in r['importers']]
            trr = common_utils.to_related_repo(r, all_configs)
            transfer_related_repos.append(trr)

        try:
            result = importer_instance.validate_config(transfer_repo, call_config, transfer_related_repos)

            # For backward compatibility with plugins that don't yet return the tuple
            if isinstance(result, bool):
                valid_config = result
                message = None
            else:
                valid_config, message = result

        except Exception, e:
            _LOG.exception('Exception received from importer [%s] while validating config' % importer_type_id)
            raise PulpDataException(e.args), None, sys.exc_info()[2]

        if not valid_config:
            raise PulpDataException(message)

        # Remove old importer if one exists
        try:
            self.remove_importer(repo_id)
        except MissingResource:
            pass # it didn't exist, so no harm done

        # Let the importer plugin initialize the repository
        try:
            importer_instance.importer_added(transfer_repo, call_config)
        except Exception:
            _LOG.exception('Error initializing importer [%s] for repo [%s]' % (importer_type_id, repo_id))
            raise PulpExecutionException(), None, sys.exc_info()[2]

        # Database Update
        importer_id = importer_type_id # use the importer name as its repo ID

        importer = RepoImporter(repo_id, importer_id, importer_type_id, clean_config)
        importer_coll.save(importer, safe=True)

        return importer

    def remove_importer(self, repo_id):
        """
        Removes an importer from a repository.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @raise MissingResource: if the given repo does not exist
        @raise MissingResource: if the given repo does not have an importer
        """

        repo_coll = Repo.get_collection()
        importer_coll = RepoImporter.get_collection()

        # Validation
        repo = repo_coll.find_one({'id' : repo_id})
        if repo is None:
            raise MissingResource(repo_id)

        repo_importer = importer_coll.find_one({'repo_id' : repo_id})

        if repo_importer is None:
            raise MissingResource(repo_id)

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

        @raise MissingResource: if the given repo does not exist
        @raise MissingResource: if the given repo does not have an importer
        @raise InvalidConfiguration: if the plugin indicates the given
                configuration is invalid
        """

        repo_coll = Repo.get_collection()
        importer_coll = RepoImporter.get_collection()

        # Input Validation
        repo = repo_coll.find_one({'id' : repo_id})
        if repo is None:
            raise MissingResource(repo_id)

        repo_importer = importer_coll.find_one({'repo_id' : repo_id})
        if repo_importer is None:
            raise MissingResource(repo_id)

        importer_type_id = repo_importer['importer_type_id']
        importer_instance, plugin_config = plugin_loader.get_importer_by_id(importer_type_id)

        # The supplied config is a delta of changes to make to the existing config.
        # The plugin expects a full configuration, so we apply those changes to
        # the original config and pass that to the plugin's validate method.
        merged_config = dict(repo_importer['config'])

        # The convention is that None in an update is removing the value and
        # setting it to the default. Find all such properties in this delta and
        # remove them from the existing config if they are there.
        unset_property_names = [k for k in importer_config if importer_config[k] is None]
        for key in unset_property_names:
            merged_config.pop(key, None)
            importer_config.pop(key, None)

        # Whatever is left over are the changed/added values, so merge them in.
        merged_config.update(importer_config)

        # Let the importer plugin verify the configuration
        call_config = PluginCallConfiguration(plugin_config, merged_config)
        transfer_repo = common_utils.to_transfer_repo(repo)
        transfer_repo.working_dir = common_utils.importer_working_dir(importer_type_id, repo_id)

        query_manager = manager_factory.repo_query_manager()
        related_repos = query_manager.find_with_importer_type(importer_type_id)

        transfer_related_repos = []
        for r in related_repos:

            # Don't include the repo being updated in this list
            if r['id'] == repo_id:
                continue

            all_configs = [d['config'] for d in r['importers']]
            trr = common_utils.to_related_repo(r, all_configs)
            transfer_related_repos.append(trr)

        try:
            result = importer_instance.validate_config(transfer_repo, call_config, transfer_related_repos)

            # For backward compatibility with plugins that don't yet return the tuple
            if isinstance(result, bool):
                valid_config = result
                message = None
            else:
                valid_config, message = result
        except Exception, e:
            _LOG.exception('Exception received from importer [%s] while validating config for repo [%s]' % (importer_type_id, repo_id))
            raise PulpDataException(e.args), None, sys.exc_info()[2]

        if not valid_config:
            raise PulpDataException(message)

        # If we got this far, the new config is valid, so update the database
        repo_importer['config'] = merged_config
        importer_coll.save(repo_importer, safe=True)

        return repo_importer

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

    def add_sync_schedule(self, repo_id, schedule_id):
        """
        Adds a sync schedule for a repo to the importer.
        @param repo_id:
        @param schedule_id:
        @return:
        """
        collection = RepoImporter.get_collection()
        importer = collection.find_one({'repo_id': repo_id})
        if importer is None:
            raise MissingResource(importer=repo_id)
        if schedule_id in importer['scheduled_syncs']:
            return
        collection.update({'_id': importer['_id']},
                          {'$push': {'scheduled_syncs': schedule_id}},
                          safe=True)

    def remove_sync_schedule(self, repo_id, schedule_id):
        """
        Removes a sync schedule for a repo from the importer.
        @param repo_id:
        @param schedule_id:
        @return:
        """
        collection = RepoImporter.get_collection()
        importer = collection.find_one({'repo_id': repo_id})
        if importer is None:
            raise MissingResource(importer=repo_id)
        if schedule_id not in importer['scheduled_syncs']:
            return
        collection.update({'_id': importer['_id']},
                          {'$pull': {'scheduled_syncs': schedule_id}},
                          safe=True)

    def list_sync_schedules(self, repo_id):
        """
        List the sync schedules currently defined for the repo.
        @param repo_id:
        @return:
        """
        collection = RepoImporter.get_collection()
        importer = collection.find_one({'repo_id': repo_id})
        if importer is None:
            raise MissingResource(importer=repo_id)
        return importer['scheduled_syncs']


