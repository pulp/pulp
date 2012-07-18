# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
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
import re
import sys
import uuid

from pulp.plugins.loader import api as plugin_api
from pulp.plugins.config import PluginCallConfiguration
from pulp.server.db.model.repo_group import RepoGroup, RepoGroupDistributor
from pulp.server.exceptions import InvalidValue, MissingResource, PulpDataException, PulpExecutionException
from pulp.server.managers import factory as manager_factory
from pulp.server.managers.repo import _common as common_utils

# -- constants ----------------------------------------------------------------

_DISTRIBUTOR_ID_REGEX = re.compile(r'^[\-_A-Za-z0-9]+$') # letters, numbers, underscore, hyphen

_LOG = logging.getLogger(__name__)

# -- manager ------------------------------------------------------------------

class RepoGroupDistributorManager(object):

    def get_distributor(self, repo_group_id, distributor_id):
        """
        Returns an individual distributor on the given repo group, raising
        an exception if one does not exist at the given ID.

        @param repo_group_id: identifies the repo group
        @type  repo_group_id: str

        @param distributor_id: identifies the distributor
        @type  distributor_id: str

        @return: SON representation of the distributor
        @rtype:  dict

        @raise MissingResource: if either there is no distributor for the
        given group ID/distributor ID pair or the group itself does not exist
        """

        # Check the group's existence for the exception contract first
        manager_factory.repo_group_query_manager().get_group(repo_group_id)

        # Check for the distributor if we know the group exists
        spec = {
            'repo_group_id' : repo_group_id,
            'id' : distributor_id,
        }
        distributor = RepoGroupDistributor.get_collection().find_one(spec)

        if distributor is None:
            raise MissingResource(repo_group=repo_group_id, distributor=distributor_id)

        return distributor

    def find_distributors(self, repo_group_id):
        """
        Returns all distributors on the given repo group, returning an empty
        list if none exist.

        @param repo_group_id: identifies the repo group
        @type  repo_group_id: str

        @return: list of SON representations of the group's distributors
        @rtype:  list

        @raise MissingResource: if the group does not exist
        """
        group = RepoGroup.get_collection().find_one({'id' : repo_group_id})
        if group is None:
            raise MissingResource(repo_group=repo_group_id)

        spec = {'repo_group_id' : repo_group_id}
        distributors = list(RepoGroupDistributor.get_collection().find(spec))
        return distributors

    def add_distributor(self, repo_group_id, distributor_type_id, group_plugin_config,
                        distributor_id=None):
        """
        Adds an association from the given repository group to a distributor.
        The assocation will be tracked through the distributor_id; each
        distributor on a given group must have a unique ID. If this is not
        specified, one will be generated. If a distributor already exists on the
        group with a given ID, the existing one will be removed and replaced
        with the newly configured one.

        @param repo_group_id: identifies the repo group
        @type  repo_group_id: str

        @param distributor_type_id: type of distributor being added; must reference
               one of the installed group distributors
        @type  distributor_type_id: str

        @param group_plugin_config: config to use for the distributor for this group alone
        @type  group_plugin_config: dict

        @param distributor_id: if specified, the newly added distributor will be
               referenced by this value and the group id; if omitted one will
               be generated
        @type  distributor_id: str

        @return: database representation of the added distributor
        @rtype:  dict

        @raise MissingResource: if the group doesn't exist
        @raise InvalidValue: if a distributor ID is provided and is not valid
        @raise PulpDataException: if the plugin indicates the config is invalid
        @raise PulpExecutionException: if the plugin raises an exception while
               initializing the newly added distributor
        """
        distributor_coll = RepoGroupDistributor.get_collection()

        query_manager = manager_factory.repo_group_query_manager()

        # Validation
        group = query_manager.get_group(repo_group_id) # will raise MissingResource

        if not plugin_api.is_valid_group_distributor(distributor_type_id):
            raise InvalidValue(['distributor_type_id'])

        # Determine the ID for the distributor on this repo
        if distributor_id is None:
            distributor_id = str(uuid.uuid4())
        else:
            # Validate if one was passed in
            if not is_distributor_id_valid(distributor_id):
                raise InvalidValue(['distributor_id'])

        distributor_instance, plugin_config = plugin_api.get_group_distributor_by_id(distributor_type_id)

        # Convention is that a value of None means unset. Remove any keys that
        # are explicitly set to None so the plugin will default them.
        clean_config = None
        if group_plugin_config is not None:
            clean_config = dict([(k, v) for k, v in group_plugin_config.items() if v is not None])

        # Let the plugin validate the configuration
        call_config = PluginCallConfiguration(plugin_config, clean_config)
        transfer_group = common_utils.to_transfer_repo_group(group)
        transfer_group.working_dir = common_utils.distributor_working_dir(distributor_type_id, repo_group_id)

        # Load the related groups which is needed for the validation
        transfer_related_groups = related_groups(distributor_type_id)

        # Request the plugin validate the configuration
        try:
            is_valid, message = distributor_instance.validate_config(transfer_group, call_config, transfer_related_groups)

            if not is_valid:
                raise PulpDataException(message)
        except Exception, e:
            _LOG.exception('Exception received from distributor [%s] while validating config' % distributor_type_id)
            raise PulpDataException(e.args), None, sys.exc_info()[2]

        # Remove the old distributor if it exists
        try:
            self.remove_distributor(repo_group_id, distributor_id, force=False)
        except MissingResource:
            pass # if it didn't exist, no problem

        # Invoke the appopriate plugin lifecycle method
        try:
            distributor_instance.distributor_added(transfer_group, call_config)
        except Exception, e:
            _LOG.exception('Error initializing distributor [%s] for group [%s]' % (distributor_type_id, repo_group_id))
            raise PulpExecutionException(), None, sys.exc_info()[2]

        # Finally, update the database
        distributor = RepoGroupDistributor(distributor_id, distributor_type_id, repo_group_id, clean_config)
        distributor_coll.save(distributor)

        return distributor

    def remove_distributor(self, repo_group_id, distributor_id, force=False):
        """
        Removes a distributor from a group.

        @param repo_group_id: identifies the group
        @type  repo_group_id: str

        @param distributor_id: identifies the distributor on the group
        @type  distributor_id: str

        @param force: if true, the distributor will be removed from the database
               regardless of whether or not the plugin's clean up method raises
               an exception

        @raise MissingResource: if there is no group or distributor with the
               given ID
        @raise PulpExecutionException: if the distributor raises an error on cleanup
        """
        distributor_coll = RepoGroupDistributor.get_collection()

        # Validation - calls will raise MissingResource
        group = manager_factory.repo_group_query_manager().get_group(repo_group_id)
        distributor = self.get_distributor(repo_group_id, distributor_id)

        # Call the distributor's cleanup method
        distributor_type_id = distributor['distributor_type_id']
        distributor_instance, plugin_config = plugin_api.get_group_distributor_by_id(distributor_type_id)

        call_config = PluginCallConfiguration(plugin_config, distributor['config'])
        transfer_group = common_utils.to_transfer_repo_group(group)
        transfer_group.working_dir = common_utils.distributor_working_dir(distributor_type_id, repo_group_id)

        try:
            distributor_instance.distributor_removed(transfer_group, call_config)
        except Exception, e:
            _LOG.exception('Exception cleaning up distributor [%s] on group [%s]' % (distributor_id, repo_group_id))

            if not force:
                raise PulpExecutionException(), None, sys.exc_info()[2]

        # Clean up the database
        distributor_coll.remove(distributor, safe=True)

    def update_distributor_config(self, repo_group_id, distributor_id, distributor_config):
        """
        Attempts to update the saved configuration for the given distributor.
        The distributor will be asked if the new configuration is valid. If
        not, this method will raise an error and the existing configuration
        will remain unchanged.

        @param repo_group_id: identifies the group
        @type  repo_group_id: str

        @param distributor_id: identifies the distributor on the group
        @type  distributor_id: str

        @param distributor_config: new configuration values to use
        @type  distributor_config: dict

        @return: the updated distributor
        @rtype:  dict

        @raise MissingResource: if the given group or distributor do not exist
        @raise PulpDataException: if the plugin indicates the new configuration
               is invalid
        """

        # Validation - calls will raise MissingResource
        group_manager = manager_factory.repo_group_query_manager()
        group = group_manager.get_group(repo_group_id)
        distributor = self.get_distributor(repo_group_id, distributor_id)

        distributor_type_id = distributor['distributor_type_id']
        distributor_instance, plugin_config = plugin_api.get_group_distributor_by_id(distributor_type_id)

        # Resolve the requested changes into the existing config
        merged_config = process_update_config(distributor['config'], distributor_config)

        # Request the distributor validate the new configuration
        call_config = PluginCallConfiguration(plugin_config, merged_config)
        transfer_group = common_utils.to_transfer_repo_group(group)
        transfer_group.working_dir = common_utils.group_distributor_working_dir(distributor_type_id, repo_group_id)
        transfer_related_groups = related_groups(distributor_type_id, omit_group_id=repo_group_id)

        # Request the plugin validate the configuration
        try:
            is_valid, message = distributor_instance.validate_config(transfer_group, call_config, transfer_related_groups)

            if not is_valid:
                raise PulpDataException(message)
        except Exception, e:
            _LOG.exception('Exception received from distributor [%s] while validating config' % distributor_type_id)
            raise PulpDataException(e.args), None, sys.exc_info()[2]

        # If we got this far, the merged_config is valid
        distributor['config'] = merged_config
        RepoGroupDistributor.get_collection().save(distributor, safe=True)

        return distributor

    def get_distributor_scratchpad(self, repo_group_id, distributor_id):
        """
        Returns the contents of the distributor's scratchpad, raising an
        error if the group or distributor does not exist.

        This is different than the behavior of the repo scratchpad calls. Those
        should be updated when we have time. jdob, June 13, 2012.

        @return: value set for the distributor's scratchpad
        @rtype:  object
        """

        distributor = self.get_distributor(repo_group_id, distributor_id)
        scratchpad = distributor['scratchpad']
        return scratchpad

    def set_distributor_scratchpad(self, repo_group_id, distributor_id, contents):
        """
        Sets the value of the scratchpad for the given group's distributor,
        replacing the existing value if one is present.

        @param contents: value to save in the scratchpad; must be serializable
        @type  contents: object
        """

        distributor = self.get_distributor(repo_group_id, distributor_id)
        distributor['scratchpad'] = contents
        RepoGroupDistributor.get_collection().save(distributor, safe=True)

# -- functions ----------------------------------------------------------------

def process_update_config(current_config, supplied_config):
    """
    Merges together the current distributor config and the user supplied config
    for an update to apply the proper conventions. A new config is returned
    that should be considered the definitive updated config for the distributor.

    @param current_config: previous distributor config from the database
    @type  current_config: dict

    @param supplied_config: user-supplied delta for the config
    @type  supplied_config: dict

    @return: new dict instance to be used as the new distributor config value
    @rtype:  dict
    """

    # The supplied config is a delta of changes to make to the existing config.
    # The plugin expects a full configuration, so we apply those changes to
    # the original config and pass that to the plugin's validate method.
    merged_config = dict(current_config)

    # The convention is that None in an update is removing the value and
    # setting it to the default. Find all such properties in this delta and
    # remove them from the existing config if they are there.
    unset_property_names = [k for k in supplied_config if supplied_config[k] is None]
    for key in unset_property_names:
        merged_config.pop(key, None)
        supplied_config.pop(key, None)

    # Whatever is left over are the changed/added values, so merge them in.
    merged_config.update(supplied_config)

    return merged_config

def related_groups(distributor_type_id, omit_group_id=None):
    """
    Loads and converts into plugin transfer objects all groups that have a
    distributor of the given ID.

    @param omit_group_id: if specified, the given group won't be included, used
           when retrieving related groups in an update call
    @type  omit_group_id: str

    @return: list of transfer objects to pass to the plugin
    @rtype:  list
    """

    query_manager = manager_factory.repo_group_query_manager()
    related_groups = query_manager.find_with_distributor_type(distributor_type_id)

    transfer_groups = []
    for g in related_groups:
        if omit_group_id and g['id'] == omit_group_id:
            continue

        all_configs = [d['config'] for d in g['distributors']]
        trg = common_utils.to_related_repo_group(g, all_configs)
        transfer_groups.append(trg)

    return transfer_groups

def is_distributor_id_valid(distributor_id):
    """
    @return: true if the distributor ID is valid; false otherwise
    @rtype:  bool
    """
    result = _DISTRIBUTOR_ID_REGEX.match(distributor_id) is not None
    return result
