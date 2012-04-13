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

from pulp.server.content.conduits._base import BaseImporterConduit, ImporterConduitException
import pulp.server.content.conduits._common as common_utils
import pulp.server.content.types.database as types_db
from pulp.server.db.model.gc_repository import RepoContentUnit
import pulp.server.managers.factory as manager_factory

from pulp.server.managers.repo.unit_association_query import Criteria # shadow for importing by plugins

# -- constants ----------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- exceptions ---------------------------------------------------------------

class UnitImportConduitException(ImporterConduitException):
    """
    General exception that wraps any server exception resulting from a conduit call.
    """
    pass

# -- classes ------------------------------------------------------------------

class ImportUnitConduit(BaseImporterConduit):
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

    def __init__(self, source_repo_id, dest_repo_id, source_importer_id, dest_importer_id):
        BaseImporterConduit.__init__(self, dest_repo_id, dest_importer_id)

        self.source_repo_id = source_repo_id
        self.dest_repo_id = dest_repo_id

        self.source_importer_id = source_importer_id
        self.dest_importer_id = dest_importer_id

        self.__association_manager = manager_factory.repo_unit_association_manager()
        self.__association_query_manager = manager_factory.repo_unit_association_query_manager()
        self.__importer_manager = manager_factory.repo_importer_manager()

    def __str__(self):
        return _('ImportUnitConduit for repository [%(r)s]') % {'r' : self.repo_id}

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
            self.__association_manager.associate_unit_by_id(self.dest_repo_id, unit.type_id, unit.id, RepoContentUnit.OWNER_TYPE_IMPORTER, self.dest_importer_id)
            return unit
        except Exception, e:
            _LOG.exception(_('Content unit association failed [%s]' % str(unit)))
            raise UnitImportConduitException(e), None, sys.exc_info()[2]

    def get_source_units(self, criteria=None):
        """
        Returns the collection of content units associated with the source
        repository for a unit import.

        Units returned from this call will have the id field populated and are
        useable in any calls in this conduit that require the id field.

        @param criteria: used to scope the returned results or the data within;
               the Criteria class can be imported from this module
        @type  criteria: L{Criteria}

        @return: list of unit instances
        @rtype:  list of L{AssociatedUnit}
        """

        try:
            units = self.__association_query_manager.get_units_across_types(self.source_repo_id, criteria=criteria)

            all_units = []

            # Load all type definitions in use so we don't hammer the database
            unique_type_defs = set([u['unit_type_id'] for u in units])
            type_defs = {}
            for def_id in unique_type_defs:
                type_def = types_db.type_definition(def_id)
                type_defs[def_id] = type_def

            # Convert to transfer object
            for unit in units:
                type_id = unit['unit_type_id']
                u = common_utils.to_plugin_unit(unit, type_defs[type_id])
                all_units.append(u)

            return all_units

        except Exception, e:
            _LOG.exception('Exception from server requesting all content units for repository [%s]' % self.repo_id)
            raise UnitImportConduitException(e), None, sys.exc_info()[2]
