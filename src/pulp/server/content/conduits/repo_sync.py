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

Plugin implementations for repository sync will obviously vary wildly. For help
in understanding the APIs, below is a short outline of a common sync process and
its calls into this conduit:

1. Call get_units to understand what units are already associated with the
   repository being synchronized.
2. For each new unit to add to the Pulp server and associate with the repository,
   the plugin takes the following steps.:
   a. Calls init_unit which takes unit specific metadata and allows Pulp to
      populate any calculated/derived values for the unit. The result of this
      call is an object representation of the unit.
   b. Uses the storage_path field in the returned unit to save the bits for the
      unit to disk.
   c. Calls save_unit which creates/updates Pulp's knowledge of the content unit
      and creates an association between the unit and the repository
   d. If necessary, calls link_unit to establish any relationships between units.
3. For units previously associated with the repository (known from get_units)
   that should no longer be, calls remove_unit to remove that association.

Throughout the sync process, the set_progress call can be used to update the
Pulp server on the status of the sync. Pulp will make this information available
to users.
"""

from gettext import gettext as _
import logging
import sys

import pulp.server.content.conduits._common as common_utils
from pulp.server.content.conduits._base import BaseImporterConduit, ImporterConduitException
import pulp.server.content.types.database as types_db
from pulp.server.content.plugins.model import Unit, SyncReport
import pulp.server.dispatch.factory as dispatch_factory
from pulp.server.exceptions import MissingResource
import pulp.server.managers.factory as manager_factory
from pulp.server.managers.repo.unit_association import OWNER_TYPE_IMPORTER

from pulp.server.managers.repo.unit_association_query import Criteria # shadow for importing by plugins

# -- constants ---------------------------------------------------------------

_LOG = logging.getLogger(__name__)

# -- exceptions --------------------------------------------------------------

class RepoSyncConduitException(ImporterConduitException):
    """
    General exception that wraps any server exception coming out of a conduit
    call.
    """
    pass

# -- classes -----------------------------------------------------------------

class RepoSyncConduit(BaseImporterConduit):
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
                 importer_id,
                 progress_callback=None):
        """
        @param repo_id: identifies the repo being synchronized
        @type  repo_id: str

        @param importer_id: identifies the importer performing the sync
        @type  importer_id: str

        @param progress_callback: used to update the server's knowledge of the
                                  sync progress
        @type  progress_callback: TBD
        """
        BaseImporterConduit.__init__(self, repo_id, importer_id)

        self.__repo_manager = manager_factory.repo_manager()
        self.__importer_manager = manager_factory.repo_importer_manager()
        self.__sync_manager = manager_factory.repo_sync_manager()
        self.__association_manager = manager_factory.repo_unit_association_manager()
        self.__association_query_manager = manager_factory.repo_unit_association_query_manager()
        self.__content_manager = manager_factory.content_manager()
        self.__content_query_manager = manager_factory.content_query_manager()
        self.__progress_callback = progress_callback

        self._added_count = 0
        self._updated_count = 0
        self._removed_count = 0

    def __str__(self):
        return _('RepoSyncConduit for repository [%(r)s]') % {'r' : self.repo_id}

    # -- public ---------------------------------------------------------------

    def set_progress(self, status):
        """
        Informs the server of the current state of the sync operation. The
        contents of the status is dependent on how the importer
        implementation chooses to divide up the sync process.

        @param status: contains arbitrary data to describe the state of the
               sync; the contents may contain whatever information is relevant
               to the importer implementation so long as it is serializable
        @type  status: dict
        """
        try:
            context = dispatch_factory.context()
            context.report_progress(status)
        except Exception, e:
            _LOG.exception('Exception from server setting progress for repository [%s]' % self.repo_id)
            try:
                _LOG.error('Progress value: %s' % str(status))
            except:
                # Best effort to print this, but if its that grossly unserializable
                # the log will tank and we don't want that exception to bubble up
                pass
            raise RepoSyncConduitException(e), None, sys.exc_info()[2]

    # -- unit lifecycle -------------------------------------------------------

    def get_units(self, criteria=None):
        """
        Returns the collection of content units associated with the repository
        being synchronized. 

        Units returned from this call will have the id field populated and are
        useable in any calls in this conduit that require the id field.

        @param criteria: used to scope the returned results or the data within;
               the Criteria class can be imported from this module
        @type  criteria: L{Criteria}

        @return: list of unit instances
        @rtype:  list of L{AssociatedUnit}
        """

        try:
            units = self.__association_query_manager.get_units_across_types(self.repo_id, criteria=criteria)

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
            raise RepoSyncConduitException(e), None, sys.exc_info()[2]

    def init_unit(self, type_id, unit_key, metadata, relative_path):
        """
        Initializes the Pulp representation of a content unit. The conduit will
        use the provided information to generate any unit metadata that it needs
        to. A populated transfer object representation of the unit will be
        returned from this call. The returned unit should be used in subsequent
        calls to this conduit.

        This call makes no changes to the Pulp server. At the end of this call,
        the unit's id field will *not* be populated.

        The unit_key and metadata will be merged as they are saved in Pulp to
        form the full representation of the unit. If values are specified in
        both dictionaries, the unit_key value takes precedence.

        If the importer wants to save the bits for the unit, the relative_path
        value should be used to indicate a unique -- with respect to the type
        of unit -- relative path where it will be saved. Pulp will convert this
        into an absolute path on disk where the unit should actually be saved.
        The absolute path is stored in the returned unit object.

        @param type_id: must correspond to a type definition in Pulp
        @type  type_id: str

        @param unit_key: dictionary of whatever fields are necessary to uniquely
                         identify this unit from others of the same type
        @type  unit_key: dict

        @param metadata: dictionary of key-value pairs to describe the unit
        @type  metadata: dict

        @param relative_path: see above; may be None
        @type  relative_path: str

        @return: object representation of the unit, populated by Pulp with both
                 provided and derived values
        @rtype:  L{Unit}
        """

        try:
            # Generate the storage location
            if relative_path is not None:
                path = self.__content_query_manager.request_content_unit_file_path(type_id, relative_path)
            else:
                path = None
            u = Unit(type_id, unit_key, metadata, path)
            return u
        except Exception, e:
            _LOG.exception('Exception from server requesting unit filename for relative path [%s]' % relative_path)
            raise RepoSyncConduitException(e), None, sys.exc_info()[2]

    def save_unit(self, unit):
        """
        Performs two distinct steps on the Pulp server:
        - Creates or updates Pulp's knowledge of the content unit.
        - Associates the unit to the repository being synchronized.

        This call is idempotent. If the unit already exists or the association
        already exists, this call will have no effect.

        A reference to the provided unit is returned from this call. This call
        will populate the unit's id field with the UUID for the unit.

        @param unit: unit object returned from the init_unit call
        @type  unit: L{Unit}

        @return: object reference to the provided unit, its state updated from the call
        @rtype:  L{Unit}
        """
        try:
            # Save or update the unit
            pulp_unit = common_utils.to_pulp_unit(unit)
            try:
                existing_unit = self.__content_query_manager.get_content_unit_by_keys_dict(unit.type_id, unit.unit_key)
                unit.id = existing_unit['_id']
                self.__content_manager.update_content_unit(unit.type_id, unit.id, pulp_unit)
                self._updated_count += 1
            except MissingResource:
                unit.id = self.__content_manager.add_content_unit(unit.type_id, None, pulp_unit)
                self._added_count += 1

            # Associate it with the repo
            self.__association_manager.associate_unit_by_id(self.repo_id, unit.type_id, unit.id, OWNER_TYPE_IMPORTER, self.importer_id)

            return unit
        except Exception, e:
            _LOG.exception(_('Content unit association failed [%s]' % str(unit)))
            raise RepoSyncConduitException(e), None, sys.exc_info()[2]

    def remove_unit(self, unit):
        """
        Removes the association between the given content unit and the repository
        being synchronized.

        This call will only remove the association owned by this importer
        between the repository and unit. If the unit was manually associated by
        a user, the repository will retain that instance of the association.

        This call does not delete Pulp's representation of the unit in its
        database. If this call removes the final association of the unit to a
        repository, the unit will become "orphaned" and will be deleted from
        Pulp outside of this plugin.

        Units passed to this call must have their id fields set by the Pulp server.

        This call is idempotent. If no association, owned by this importer, exists
        between the unit and repository, this call has no effect.

        @param unit: unit object (must have its id value set)
        @type  unit: L{Unit}
        """

        try:
            self.__association_manager.unassociate_unit_by_id(self.repo_id, unit.type_id, unit.id, OWNER_TYPE_IMPORTER, self.importer_id)
            self._removed_count += 1
        except Exception, e:
            _LOG.exception(_('Content unit unassociation failed'))
            raise RepoSyncConduitException(e), None, sys.exc_info()[2]

    def link_unit(self, from_unit, to_unit, bidirectional=False):
        """
        Creates a reference between two content units. The semantics of what
        this relationship means depends on the types of content units being
        used; this call simply ensures that Pulp will save and make available
        the indication that a reference exists from one unit to another.

        By default, the reference will only exist on the from_unit side. If
        the bidirectional flag is set to true, a second reference will be created
        on the to_unit to refer back to the from_unit.

        Units passed to this call must have their id fields set by the Pulp server.

        @param from_unit: owner of the reference
        @type  from_unit: L{Unit}

        @param to_unit: will be referenced by the from_unit
        @type  to_unit: L{Unit}
        """
        try:
            self.__content_manager.link_referenced_content_units(from_unit.type_id, from_unit.id, to_unit.type_id, [to_unit.id])

            if bidirectional:
                self.__content_manager.link_referenced_content_units(to_unit.type_id, to_unit.id, from_unit.type_id, [from_unit.id])
        except Exception, e:
            _LOG.exception(_('Child link from parent [%s] to child [%s] failed' % (str(from_unit), str(to_unit))))
            raise RepoSyncConduitException(e), None, sys.exc_info()[2]

    def build_success_report(self, summary, details):
        """
        Creates the SyncReport instance that needs to be returned to the Pulp
        server at the end of a successful sync_repo call.

        The added, updated, and removed unit count fields will be populated with
        the tracking counters maintained by the conduit based on calls into it.
        If these are inaccurate for a given plugin's implementation, the counts
        can be changed in the returned report before returning it to Pulp.

        @param summary: short log of the sync; may be None but probably shouldn't be
        @type  summary: any serializable

        @param details: potentially longer log of the sync; may be None
        @type  details: any serializable
        """
        r = SyncReport(True, self._added_count, self._updated_count,
                       self._removed_count, summary, details)
        return r

    def build_failure_report(self, summary, details):
        """
        Creates the SyncReport instance that needs to be returned to the Pulp
        server at the end of a sync_repo call. The report built in this fashion
        will indicate the sync has gracefully failed (as compared to an
        unexpected exception bubbling up).

        The added, updated, and removed unit count fields will be populated with
        the tracking counters maintained by the conduit based on calls into it.
        If these are inaccurate for a given plugin's implementation, the counts
        can be changed in the returned report before returning it to Pulp. This
        data will capture how far it got before building the report and should
        be overridden if the plugin attempts to do some form of rollback due to
        the encountered error.

        @param summary: short log of the sync; may be None but probably shouldn't be
        @type  summary: any serializable

        @param details: potentially longer log of the sync; may be None
        @type  details: any serializable
        """
        r = SyncReport(False, self._added_count, self._updated_count,
                       self._removed_count, summary, details)
        return r
