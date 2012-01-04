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

"""
Contains the definitions for all classes related to the importer's API for
interacting with the Pulp server when importing units.
"""

from gettext import gettext as _
import logging
import sys

from pulp.server.db.model.gc_repository import RepoContentUnit

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- exceptions ---------------------------------------------------------------

class ImportConduitException(Exception):
    """
    General exception that wraps any server exception resulting from a conduit call.
    """
    pass

# -- classes ------------------------------------------------------------------

class ImportUnitConduit:
    """
    Used to interact with the Pulp server while importing units into a
    repository. Instances of this class should *not* be cached between import
    calls. Each call will be issued its own conduit instance that is scoped
    to a single import.

    Instances of this class are thread-safe. The importer implementation is
    allowed to do whatever threading makes sense to optimize the import.
    Calls into this instance do not have to be coordinated for thread safety,
    the instance will take care of it itself.
    """

    def __init__(self, repo_id, importer_id, repo_association_manager,
                 repo_importer_manager):

        self.repo_id = repo_id
        self.importer_id = importer_id

        self.__association_manager = repo_association_manager
        self.__importer_manager = repo_importer_manager

    # -- public ---------------------------------------------------------------

    def associate_unit(self, unit):
        """
        Associates the given unit with the destination repository for the import.

        This call is idempotent. If the association already exists, this call
        will have no effect.

        @param unit: unit object returned from the init_unit call
        @type  unit: L{Unit}

        @return: object reference to the provided unit
        @rtype:  L{Unit}
        """

        try:
            self.__association_manager.associate_unit_by_id(self.repo_id, unit.type_id, unit.id, RepoContentUnit.OWNER_TYPE_IMPORTER, self.importer_id)
            return unit
        except Exception, e:
            _LOG.exception(_('Content unit association failed [%s]' % str(unit)))
            raise ImportConduitException(e), None, sys.exc_info()[2]

    # -- importer utilities ---------------------------------------------------

    def get_scratchpad(self):
        """
        Returns the value set in the scratchpad for this repository. If no
        value has been set, None is returned.

        @return: value saved for the repository being synchronized
        @rtype:  <serializable>
        """
        try:
            return self.__importer_manager.get_importer_scratchpad(self.repo_id)
        except Exception, e:
            _LOG.exception(_('Error getting scratchpad for repo [%s]' % self.repo_id))
            raise ImportConduitException(e), None, sys.exc_info()[2]

    def set_scratchpad(self, value):
        """
        Saves the given value to the scratchpad for this repository. It can later
        be retrieved in subsequent syncs through get_scratchpad. The type for
        the given value is anything that can be stored in the database (string,
        list, dict, etc.).

        @param value: will overwrite the existing scratchpad
        @type  value: <serializable>
        """
        try:
            self.__importer_manager.set_importer_scratchpad(self.repo_id, value)
        except Exception, e:
            _LOG.exception(_('Error setting scratchpad for repo [%s]' % self.repo_id))
            raise ImportConduitException(e), None, sys.exc_info()[2]

