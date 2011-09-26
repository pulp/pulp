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
Contains the definitions for all classes related to the importer's API for
interacting with the Pulp server during a repo sync.
"""

import copy
import logging
import sys
from gettext import gettext as _

from pulp.server.managers.content.exception import ContentUnitNotFound

# -- constants ---------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- exceptions --------------------------------------------------------------

class RepoSyncConduitException(Exception):
    """
    General exception that wraps any server exception coming out of a conduit
    call.
    """
    pass

# -- classes -----------------------------------------------------------------

class RepoSyncConduit:
    """
    Used to communicate back into the Pulp server while an importer performs
    a repo sync. Instances of this class should *not* be cached between repo
    sync runs. Each sync will be issued its own conduit instance that is scoped
    to that sync alone.

    Instances of this class are thread-safe. The importer implementation is
    allowed to do whatever threading makes sense to optimize its sync process.
    Calls into this instance do not have to be coordinated for thread safety,
    the instance will take care of it itself.
    """

    def __init__(self,
                 repo_id,
                 repo_cud_manager,
                 repo_sync_manager,
                 repo_association_manager,
                 content_manager,
                 content_query_manager,
                 progress_callback=None):
        """
        @param repo_id: identifies the repo being synchronized
        @type  repo_id: str

        @param repo_cud_manager: server manager instance for manipulating repos
        @type  repo_cud_manager: L{RepoManager}

        @param repo_sync_manager: server manager instance for sync-related operations
        @type  repo_sync_manager: L{RepoSyncManager}

        @param repo_association_manager: server manager instance for manipulating
                   repo to content unit associations
        @type  repo_association_manager: L{RepoUnitAssociationManager}

        @param content_manager: server manager instance for manipulating content
                                types and units
        @type  content_manager: L{ContentManager}

        @param content_query_manager: server manager instance for querying
                                      content types and units
        @type  content_query_manager: L{ContentQueryManager}

        @param progress_callback: used to update the server's knowledge of the
                   sync progress
        @type  progress_callback: ?
        """
        self.repo_id = repo_id

        self.__repo_manager = repo_cud_manager
        self.__sync_manager = repo_sync_manager
        self.__association_manager = repo_association_manager
        self.__content_manager = content_manager
        self.__content_query_manager = content_query_manager
        self.__progress_callback = progress_callback

    def __str__(self):
        return _('RepoSyncConduit for repository [%(r)s]') % {'r' : self.repo_id}

    # -- public ---------------------------------------------------------------

    def set_progress(self, current_step, total_steps, message):
        """
        Informs the server of the current state of the sync operation. The
        granularity of what a "step" is is dependent on how the importer
        implementation chooses to divide up the sync process.

        If the step data being set is invalid, this method will do nothing. No
        error will be thrown in the case of invalid step data.

        @param current_step: indicates where in the total process the sync is;
                             must be less than total_steps, greater than 0
        @type  current_step: int

        @param total_steps: indicates how much total work is needed; must be
                            greater than 0
        @type  total_steps: int

        @param message: message to make available to the user describing where
                        in the sync process the actual sync run is
        @type  message: str
        """

        # Validation
        if current_step < 1 or total_steps < 1 or current_step > total_steps:
            _LOG.warn('Invalid step data [current: %d, total: %d], set_progress aborting' % (current_step, total_steps))
            return

        # TODO: add hooks into tasking subsystem

        _LOG.info('Progress for repo [%s] sync: %s - %d/%d' % (self.repo_id, message, current_step, total_steps))

    def request_unit_filename(self, content_type, relative_path):
        """
        Requests the server translate the relative location of where a content
        unit should be stored into a full path on the local filesystem.

        @param content_type: the unique id of the content type
        @type  content_type: str

        @param relative_path: the path, as determined by the importer, where the
                              content unit should be stored
        @type  relative_path: str

        @return: absolute path where to store the unit
        @rtype:  str
        """

        path = self.__content_query_manager.request_content_unit_file_path(content_type, relative_path)
        return path

    def get_repo_storage_directory(self):
        """
        Returns a unique directory for the repository being synchronized where
        repository-related data can be stored.

        @return: full path to the directory into which the importer can write
                 repository files
        @rtype:  str
        """
        dir = self.__sync_manager.get_repo_storage_directory(self.repo_id)
        return dir

    def add_or_update_content_unit(self, type_id, unit_key, standard_unit_data, custom_unit_data):
        """
        Informs the server of a link between a content unit and the repo being
        syncced. This call does not distinguish between adding a new unit to
        the server v. updating an existing one; the server will resolve those
        distinctions. What this call does is ensure that a link exists between
        the repo being syncced and the given content unit.

        If the content unit already exists in the database (as determined by the
        pairing of type_id and unit_key), its metadata will be updated with the
        contents of standard_unit_data and custom_unit_data passed into this call.

        @param type_id: identifies the type of unit being added; this value must
                        be present in the server at the time of this call or an
                        error will be raised
        @type  type_id: str

        @param unit_key: key/value pairs uniquely identifying this unit from all
                         other units of the same type; the keys in here must
                         match the unique indexes defined in the type definition
        @type  unit_key: dict

        @param standard_unit_data: key/value pairs providing the required set of
                         metadata for describing a content unit
        @type  standard_unit_data: dict

        @param custom_unit_data: key/value pairs describing any type-specific
                         metadata for the content unit; no validation will be
                         performed on the data included here
        @type  custom_unit_data: dict
        """
        unit_id = None
        try:
            unit = self.__content_query_manager.get_content_unit_by_keys_dict(type_id, unit_key)
            unit_id = unit['_id']
            self.__content_manager.update_content_unit(type_id, unit_id, custom_unit_data)
        except ContentUnitNotFound:
            consolidated_data = copy.copy(standard_unit_data)
            consolidated_data.update(custom_unit_data)
            unit_id = consolidated_data.get('_id', None)
            unit_id = self.__content_manager.add_content_unit(type_id, unit_id, consolidated_data)
        return unit_id

    def associate_content_unit(self, type_id, unit_id):
        """
        Creates a relationship between the repo being synchronized and the
        content unit identified by the given key. The unit must have been
        previously added to the server through the add_or_update_content_unit
        call.

        @param type_id: identifies the type of content unit being associated
        @type  type_id: str

        @param unit_id: identifies the content unit itself
        @type  unit_id: str
        """
        try:
            self.__association_manager.associate_unit_by_id(self.repo_id, type_id, unit_id)
        except:
            _LOG.exception(_('Content unit association failed'))
            raise RepoSyncConduitException(), None, sys.exc_info()[2]

    def associate_content_units(self, type_id, unit_id_list):
        """
        Bulk operation to create multiple associations. This call is optimized
        for multiple associations and is preferred to looping over multiple
        calls to associate_content_unit.

        @param type_id: identifies the type of content unit being associated
        @type  type_id: str

        @param unit_id_list: list of unit IDs to associate
        @type  unit_id_list: list of str
        """
        try:
            self.__association_manager.associate_all_by_ids(self.repo_id, type_id, unit_id_list)
        except:
            _LOG.exception(_('Multiple unit association failed'))
            raise RepoSyncConduitException(), None, sys.exc_info()[2]

    def unassociate_content_unit(self, type_id, unit_id):
        """
        Unassociates the given content unit from the repo being syncced. The
        unit is not deleted from the server's database. If for some reason the
        content unit is not associated with the repo, this call has no effect.

        @param type_id: identifies the type of unit being associated
        @type  type_id: str

        @param unit_id: identifies the content unit itself
        @type  unit_id: str
        """
        try:
            self.__association_manager.unassociate_unit_by_id(self.repo_id, type_id, unit_id)
        except:
            _LOG.exception(_('Content unit unassociation failed'))
            raise RepoSyncConduitException(), None, sys.exc_info()[2]

    def unassociate_content_units(self, type_id, unit_id_list):
        """
        Bulk operation for removing multiple associations. This call is optimized
        for multiple association removals and is preferred to looping over
        multiple calls to unassociate_content_unit.

        @param type_id: identifies the type of content unit being associated
        @type  type_id: str

        @param unit_id_list: list of unit IDs to unassociate
        @type  unit_id_list: list of str
        """
        try:
            self.__association_manager.unassociate_all_by_ids(self.repo_id, type_id, unit_id_list)
        except:
            _LOG.exception(_('Multiple unit unassociations failed'))
            raise RepoSyncConduitException(), None, sys.exc_info()[2]

    def add_repo_metadata_values(self, values_dict):
        """
        Adds or updates metadata on the repo itself to further describe its
        contents. Existing values that are not included in the argument to this
        call are left unchanged.

        @param values_dict: pairing of keys/values to add to the repo
        @type  values_dict: dict
        """

        try:
            self.__repo_manager.add_metadata_values(self.repo_id, values_dict)
        except:
            _LOG.exception(_('Error adding metadata values to repo'))
            raise RepoSyncConduitException(), None, sys.exc_info()[2]

    def remove_repo_metadata_values(self, value_keys):
        """
        Removes repo metadata stored at the given keys. If there is no metadata
        entry for a given key, nothing is done and no error is raised.

        @param value_keys: list of keys to remove from the repo's metadata
        @type  value_keys: list of str
        """

        try:
            self.__repo_manager.remove_metadata_values(self.repo_id, value_keys)
        except:
            _LOG.exception(_('Exception removing metadata values from repo'))
            raise RepoSyncConduitException(), None, sys.exc_info()[2]

    def get_unit_keys_for_repo(self, type_id=None):
        """
        Returns a list of keys for units associated with the repo being
        synchronized. This can be used to determine units that were once
        associated but were not present in the latest sync.

        @param type_id: optional; if specified, only keys for units of the
                        given type are returned
        """
        unit_keys = []
        content_ids = self.__association_manager.get_unit_ids(self.repo_id, type_id)
        for content_type_id, unit_ids in content_ids:
            unit_keys.extend(self.__content_query_manager.get_content_unit_keys(type_id, unit_ids)[1])
        return unit_keys

    def get_scratchpad(self):
        """
        Returns the value set in the scratchpad for this repository. If no
        value has been set, None is returned.
        """
        return self.__repo_manager.get_importer_scratchpad(self.repo_id)

    def set_scratchpad(self, value):
        """
        Saves the given value to the scratchpad for this repository. It can later
        be retrieved in subsequent syncs through get_scratchpad. The type for
        the given value is anything that can be stored in the database (string,
        list, dict, etc.).
        """
        self.__repo_manager.set_importer_scratchpad(self.repo_id, value)
