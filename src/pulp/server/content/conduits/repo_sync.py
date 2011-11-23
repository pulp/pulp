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

from gettext import gettext as _
import logging
import sys

import pulp.server.content.conduits._common as common_utils
import pulp.server.content.types.database as types_db
from pulp.server.content.plugins.data import Unit
from pulp.server.managers.content._exceptions import ContentUnitNotFound

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
    to that run of the sync alone.

    Instances of this class are thread-safe. The importer implementation is
    allowed to do whatever threading makes sense to optimize its sync process.
    Calls into this instance do not have to be coordinated for thread safety,
    the instance will take care of it itself.
    """

    def __init__(self,
                 repo_id,
                 repo_cud_manager,
                 repo_importer_manager,
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

        @param repo_importer_manager: server manager for manipulating importers
        @type  repo_importer_manager: L{RepoImporterManager}

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
        @type  progress_callback: TBD
        """
        self.repo_id = repo_id

        self.__repo_manager = repo_cud_manager
        self.__importer_manager = repo_importer_manager
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

    # -- unit lifecycle -------------------------------------------------------

    def get_units(self):
        """
        Returns the collection of content units associated with the repository
        being synchronized. 

        @return: list of unit instances
        @rtype:  list of L{Unit}
        """

        try:
            all_units = []

            units_by_type = self.__association_manager.get_units(self.repo_id)

            for type_id, type_units in units_by_type.items():

                type_def = types_db.type_definition(type_id)
                if type_def is None:
                    continue

                for unit in type_units:
                    u = common_utils.to_plugin_unit(unit, type_def)
                    all_units.append(u)

            return all_units

        except Exception, e:
            _LOG.exception('Exception from server requesting all content units for repository [%s]' % self.repo_id)
            raise RepoSyncConduitException(e), None, sys.exc_info()[2]

    def init_unit(self, type_id, unit_key, metadata, relative_path):

        try:
            # Generate the storage location
            path = self.__content_query_manager.request_content_unit_file_path(type_id, relative_path)
            u = Unit(type_id, unit_key, metadata, path)
            return u
        except Exception, e:
            _LOG.exception('Exception from server requesting unit filename for relative path [%s]' % relative_path)
            raise RepoSyncConduitException(e), None, sys.exc_info()[2]

    def save_unit(self, unit):
        """
        Creates a relationship between the repo being synchronized and the
        content unit identified by the given key. The unit must have been
        previously added to the server through the add_or_update_content_unit
        call.

        """
        try:
            unit_id = None

            # Save or update the unit
            pulp_unit = common_utils.to_pulp_unit(unit)
            try:
                existing_unit = self.__content_query_manager.get_content_unit_by_keys_dict(unit.type_id, unit.unit_key)
                unit.id = existing_unit['_id']
                self.__content_manager.update_content_unit(unit.type_id, unit_id, pulp_unit)
            except ContentUnitNotFound:
                unit.id = self.__content_manager.add_content_unit(unit.type_id, None, pulp_unit)

            # Associate it with the repo
            self.__association_manager.associate_unit_by_id(self.repo_id, unit.type_id, unit.id)

            return unit
        except Exception, e:
            _LOG.exception(_('Content unit association failed [%s]' % str(unit)))
            raise RepoSyncConduitException(e), None, sys.exc_info()[2]

    def remove_unit(self, unit):
        try:
            self.__association_manager.unassociate_unit_by_id(self.repo_id, unit.type_id, unit.id)
        except Exception, e:
            _LOG.exception(_('Content unit unassociation failed'))
            raise RepoSyncConduitException(e), None, sys.exc_info()[2]

    def link_child_unit(self, parent_unit, child_unit):
        """
        Must be called _after_ save_unit on both parent and child.
        """
        try:
            self.__content_manager.link_child_content_units(parent_unit.type_id, parent_unit.id, child_unit.type_id, [child_unit.id])
        except Exception, e:
            _LOG.exception(_('Child link from parent [%s] to child [%s] failed' % (str(parent_unit), str(child_unit))))
            raise RepoSyncConduitException(e), None, sys.exc_info()[2]

    # -- importer utilities ---------------------------------------------------

    def get_scratchpad(self):
        """
        Returns the value set in the scratchpad for this repository. If no
        value has been set, None is returned.
        """
        return self.__importer_manager.get_importer_scratchpad(self.repo_id)

    def set_scratchpad(self, value):
        """
        Saves the given value to the scratchpad for this repository. It can later
        be retrieved in subsequent syncs through get_scratchpad. The type for
        the given value is anything that can be stored in the database (string,
        list, dict, etc.).
        """
        self.__importer_manager.set_importer_scratchpad(self.repo_id, value)
