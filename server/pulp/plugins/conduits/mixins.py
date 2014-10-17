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

from gettext import gettext as _
import logging
import sys

from pymongo.errors import DuplicateKeyError

import pulp.plugins.conduits._common as common_utils
from pulp.plugins.model import Unit, PublishReport
from pulp.plugins.types import database as types_db
from pulp.server.async.task_status_manager import TaskStatusManager
from pulp.server.async.tasks import get_current_task_id
from pulp.server.exceptions import MissingResource
import pulp.server.managers.factory as manager_factory

# Unused in this class but imported here so plugins don't have to reach
# into server packages directly
from pulp.server.db.model.criteria import UnitAssociationCriteria, Criteria

# -- constants ----------------------------------------------------------------

logger = logging.getLogger(__name__)

# -- exceptions ---------------------------------------------------------------

class ImporterConduitException(Exception):
    """
    General exception that wraps any exception coming out of the Pulp server.
    """
    pass


class DistributorConduitException(Exception):
    """
    General exception that wraps any exception coming out of the Pulp server.
    """
    pass


class ProfilerConduitException(Exception):
    """
    General exception that wraps any exception coming out of the Pulp server.
    """
    pass

class ContentSourcesConduitException(Exception):
    """
    General exception that wraps any exception coming out of the Pulp server.
    """
    pass

# -- mixins -------------------------------------------------------------------

class RepoScratchPadMixin(object):

    def __init__(self, repo_id, exception_class):
        self.repo_id = repo_id
        self.exception_class = exception_class

    def get_repo_scratchpad(self):
        """
        Returns the repository-level scratchpad for this repository. The
        repository-level scratchpad can be seen and edited by all importers
        and distributors on the repository. Care should be taken to not destroy
        any data set by another plugin. This may be used to communicate between
        importers, distributors and profilers relevant data for the repository.
        """
        try:
            repo_manager = manager_factory.repo_manager()
            value = repo_manager.get_repo_scratchpad(self.repo_id)
            return value
        except Exception, e:
            logger.exception(_('Error getting repository scratchpad for repo [%(r)s]') % {'r' : self.repo_id})
            raise self.exception_class(e), None, sys.exc_info()[2]

    def set_repo_scratchpad(self, value):
        """
        Saves the given value to the repository-level scratchpad for this
        repository. It can be retrieved in subsequent importer, distributor
        and profiler operations through get_repo_scratchpad.

        @param value: will overwrite the existing scratchpad
        @type  value: dict

        @raise ImporterConduitException: wraps any exception that may occur
               in the Pulp server
        """
        try:
            repo_manager = manager_factory.repo_manager()
            repo_manager.set_repo_scratchpad(self.repo_id, value)
        except Exception, e:
            logger.exception(_('Error setting repository scratchpad for repo [%(r)s]') % {'r' : self.repo_id})
            raise self.exception_class(e), None, sys.exc_info()[2]

    def update_repo_scratchpad(self, scratchpad):
        """
        Update the repository scratchpad with the specified key-value pairs.
        New keys are added; existing keys are updated.
        :param scratchpad: a dict used to update the scratchpad.
        """
        try:
            manager = manager_factory.repo_manager()
            manager.update_repo_scratchpad(self.repo_id, scratchpad)
        except Exception, e:
            msg = _('Error updating repository scratchpad for repo [%(r)s]') % {'r': self.repo_id}
            logger.exception(msg)
            raise self.exception_class(e), None, sys.exc_info()[2]


class RepoScratchpadReadMixin(object):
    """
    Used for read only access to a repository's scratchpad. The intention is for
    this to be used by repository group plugins to access but not change
    the scratchpads for the repositories in the group.
    """

    def __init__(self, exception_class):
        self.exception_class = exception_class

    def get_repo_scratchpad(self, repo_id):
        """
        Returns the repository-level scratchpad for the indicated repository.

        @raise ImporterConduitException: wraps any exception that may occur
               in the Pulp server
        """
        try:
            repo_manager = manager_factory.repo_manager()
            value = repo_manager.get_repo_scratchpad(repo_id)
            return value
        except Exception, e:
            logger.exception(_('Error getting repository scratchpad for repo [%(r)s]') % {'r' : repo_id})
            raise self.exception_class(e), None, sys.exc_info()[2]


class SingleRepoUnitsMixin(object):

    def __init__(self, repo_id, exception_class):
        self.repo_id = repo_id
        self.exception_class = exception_class

    def get_units(self, criteria=None, as_generator=False):
        """
        Returns the collection of content units associated with the repository
        being operated on.

        Units returned from this call will have the id field populated and are
        usable in any calls in this conduit that require the id field.

        :param criteria: used to scope the returned results or the data within;
               the Criteria class can be imported from this module
        :type  criteria: UnitAssociationCriteria

        :return: list of unit instances
        :rtype:  list or generator of AssociatedUnit
        """
        return do_get_repo_units(self.repo_id, criteria, self.exception_class, as_generator)


class MultipleRepoUnitsMixin(object):

    def __init__(self, exception_class):
        self.exception_class = exception_class

    def get_units(self, repo_id, criteria=None, as_generator=False):
        """
        Returns the collection of content units associated with the given
        repository.

        Units returned from this call will have the id field populated and are
        usable in any calls in this conduit that require the id field.

        :param criteria: used to scope the returned results or the data within;
               the Criteria class can be imported from this module
        :type  criteria: UnitAssociationCriteria

        :return: list of unit instances
        :rtype:  list or generator of AssociatedUnit
        """
        return do_get_repo_units(repo_id, criteria, self.exception_class, as_generator)


class SearchUnitsMixin(object):

    def __init__(self, exception_class):
        self.exception_class = exception_class

    def search_all_units(self, type_id, criteria):
        """
        Searches for units of a given type in the server, regardless of their
        associations to any repositories.

        @param type_id: indicates the type of units being retrieved
        @type  type_id: str
        @param criteria: used to query which units are returned
        @type  criteria: pulp.server.db.model.criteria.Criteria

        @return: list of unit instances
        @rtype:  list of L{Unit}
        """

        try:
            query_manager = manager_factory.content_query_manager()
            units = query_manager.find_by_criteria(type_id, criteria)
            type_def = types_db.type_definition(type_id)

            transfer_units = []
            for pulp_unit in units:
                u = common_utils.to_plugin_unit(pulp_unit, type_def)
                transfer_units.append(u)

            return transfer_units

        except Exception, e:
            logger.exception('Exception from server requesting all units of type [%s]' % type_id)
            raise self.exception_class(e), None, sys.exc_info()[2]


class ImporterScratchPadMixin(object):

    def __init__(self, repo_id, importer_id):
        self.repo_id = repo_id
        self.importer_id = importer_id

    def get_scratchpad(self):
        """
        Returns the value set for the importer's private scratchpad for this
        repository. If no value has been set, None is returned.

        @return: value saved for the repository and this importer
        @rtype:  <serializable>

        @raise ImporterConduitException: wraps any exception that may occur
               in the Pulp server
        """

        try:
            importer_manager = manager_factory.repo_importer_manager()
            value = importer_manager.get_importer_scratchpad(self.repo_id)
            return value
        except Exception, e:
            logger.exception(_('Error getting scratchpad for repo [%(r)s]') % {'r' : self.repo_id})
            raise ImporterConduitException(e), None, sys.exc_info()[2]

    def set_scratchpad(self, value):
        """
        Saves the given value to the importer's private scratchpad for this
        repository. It can later be retrieved in subsequent importer operations
        through get_scratchpad. The type for the given value is anything that
        can be stored in the database (string, list, dict, etc.).

        @param value: will overwrite the existing scratchpad
        @type  value: <serializable>

        @raise ImporterConduitException: wraps any exception that may occur
               in the Pulp server
        """
        try:
            importer_manager = manager_factory.repo_importer_manager()
            importer_manager.set_importer_scratchpad(self.repo_id, value)
        except Exception, e:
            logger.exception(_('Error setting scratchpad for repo [%(r)s]') % {'r' : self.repo_id})
            raise ImporterConduitException(e), None, sys.exc_info()[2]


class DistributorScratchPadMixin(object):

    def __init__(self, repo_id, distributor_id):
        self.repo_id = repo_id
        self.distributor_id = distributor_id

    def get_scratchpad(self):
        """
        Returns the value set in the scratchpad for this repository. If no
        value has been set, None is returned.

        @return: value saved for the repository and this distributor
        @rtype:  <serializable>

        @raises DistributorConduitException: wraps any exception that may occur
                in the Pulp server
        """
        try:
            distributor_manager = manager_factory.repo_distributor_manager()
            value = distributor_manager.get_distributor_scratchpad(self.repo_id, self.distributor_id)
            return value
        except Exception, e:
            logger.exception('Error getting scratchpad for repository [%s]' % self.repo_id)
            raise DistributorConduitException(e), None, sys.exc_info()[2]

    def set_scratchpad(self, value):
        """
        Saves the given value to the scratchpad for this repository. It can later
        be retrieved in subsequent syncs through get_scratchpad. The type for
        the given value is anything that can be stored in the database (string,
        list, dict, etc.).

        @param value: will overwrite the existing scratchpad
        @type  value: <serializable>

        @raises DistributorConduitException: wraps any exception that may occur
                in the Pulp server
        """
        try:
            distributor_manager = manager_factory.repo_distributor_manager()
            distributor_manager.set_distributor_scratchpad(self.repo_id, self.distributor_id, value)
        except Exception, e:
            logger.exception('Error setting scratchpad for repository [%s]' % self.repo_id)
            raise DistributorConduitException(e), None, sys.exc_info()[2]


class RepoGroupDistributorScratchPadMixin(object):

    def __init__(self, group_id, distributor_id):
        self.group_id = group_id
        self.distributor_id = distributor_id

    def get_scratchpad(self):
        """
        Returns the value set in the scratchpad for this repository group. If no
        value has been set, None is returned.

        @return: value saved for the repository group and this distributor
        @rtype:  object

        @raises DistributorConduitException: wraps any exception that may occur
                in the Pulp server
        """
        try:
            distributor_manager = manager_factory.repo_group_distributor_manager()
            value = distributor_manager.get_distributor_scratchpad(self.group_id, self.distributor_id)
            return value
        except Exception, e:
            logger.exception('Error getting scratchpad for repository [%s]' % self.group_id)
            raise DistributorConduitException(e), None, sys.exc_info()[2]

    def set_scratchpad(self, value):
        """
        Saves the given value to the scratchpad for this repository group. It
        can later be retrieved in subsequent syncs through get_scratchpad. The
        type for the given value is anything that can be stored in the database
        (string, list, dict, etc.).

        @param value: will overwrite the existing scratchpad
        @type  value: object

        @raises DistributorConduitException: wraps any exception that may occur
                in the Pulp server
        """
        try:
            distributor_manager = manager_factory.repo_group_distributor_manager()
            distributor_manager.set_distributor_scratchpad(self.group_id, self.distributor_id, value)
        except Exception, e:
            logger.exception('Error setting scratchpad for repository [%s]' % self.group_id)
            raise DistributorConduitException(e), None, sys.exc_info()[2]


class AddUnitMixin(object):
    """
    Used to communicate back into the Pulp server while an importer performs
    commands related to adding and linking units.

    Instances of this class should *not* be cached between calls into the importer.
    Each call will be issued its own conduit instance that is scoped
    to that run of the operation alone.

    Instances of this class are thread-safe. The importer implementation is
    allowed to do whatever threading makes sense to optimize its process.
    Calls into this instance do not have to be coordinated for thread safety,
    the instance will take care of it itself.
    """

    def __init__(self, repo_id, importer_id, association_owner_type, association_owner_id):
        """
        @param repo_id: identifies the repo being synchronized
        @type  repo_id: str

        @param importer_id: identifies the importer performing the sync
        @type  importer_id: str

        @param association_owner_type: type used when creating associations;
               set to either importer or user depending on what call is being
               made into the importer
        @type  association_owner_type: str

        @param association_owner_id: ID of the association owner
        @type  association_owner_id: str
        """
        self.repo_id = repo_id
        self.importer_id = importer_id
        self.association_owner_type = association_owner_type
        self.association_owner_id = association_owner_id

        self._added_count = 0
        self._updated_count = 0

        self._association_owner_id = association_owner_id

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
        @type  relative_path: str, None

        @return: object representation of the unit, populated by Pulp with both
                 provided and derived values
        @rtype:  pulp.plugins.model.Unit
        """

        try:
            # Generate the storage location
            if relative_path is not None:
                content_query_manager = manager_factory.content_query_manager()
                path = content_query_manager.request_content_unit_file_path(type_id, relative_path)
            else:
                path = None
            u = Unit(type_id, unit_key, metadata, path)
            return u
        except Exception, e:
            logger.exception('Exception from server requesting unit filename for relative path [%s]' % relative_path)
            raise ImporterConduitException(e), None, sys.exc_info()[2]

    def save_unit(self, unit):
        """
        Performs two distinct steps on the Pulp server:
        - Creates or updates Pulp's knowledge of the content unit.
        - Associates the unit to the repository being synchronized.

        If a unit with the provided unit key already exists, it is updated with
        the attributes on the passed-in unit.

        A reference to the provided unit is returned from this call. This call
        will populate the unit's id field with the UUID for the unit.

        :param unit: unit object returned from the init_unit call
        :type  unit: Unit

        :return: object reference to the provided unit, its state updated from the call
        :rtype:  Unit
        """
        try:
            association_manager = manager_factory.repo_unit_association_manager()

            # Save or update the unit
            pulp_unit = common_utils.to_pulp_unit(unit)
            unit.id = self._update_unit(unit, pulp_unit)

            # Associate it with the repo
            association_manager.associate_unit_by_id(self.repo_id, unit.type_id, unit.id, self.association_owner_type, self.association_owner_id)

            return unit
        except Exception, e:
            logger.exception(_('Content unit association failed [%s]' % str(unit)))
            raise ImporterConduitException(e), None, sys.exc_info()[2]

    def _update_unit(self, unit, pulp_unit):
        """
        Update a unit. If it is not found, add it.

        :param unit:        the unit to be updated
        :type  unit:        pulp.plugins.model.Unit
        :param pulp_unit:   the unit to be updated, as a dict
        :type  pulp_unit:   dict

        :return:    id of the updated unit
        :rtype:     basestring
        """
        content_query_manager = manager_factory.content_query_manager()
        content_manager = manager_factory.content_manager()
        try:
            existing_unit = content_query_manager.get_content_unit_by_keys_dict(unit.type_id, unit.unit_key)
            unit_id = existing_unit['_id']
            content_manager.update_content_unit(unit.type_id, unit_id, pulp_unit)
            self._updated_count += 1
            return unit_id
        except MissingResource:
            logger.debug(_('cannot update unit; does not exist. adding instead.'))
            return self._add_unit(unit, pulp_unit)

    def _add_unit(self, unit, pulp_unit):
        """
        Add a unit. If it already exists, update it.

        This deals with a race condition where a unit might try to be updated,
        but does not exist. Before this method can complete, another workflow
        might add that same unit, causing the DuplicateKeyError below. This can
        happen if two syncs are running concurrently of repositories that have
        overlapping content.

        :param unit:        the unit to be updated
        :type  unit:        pulp.plugins.model.Unit
        :param pulp_unit:   the unit to be updated, as a dict
        :type  pulp_unit:   dict

        :return:    id of the updated unit
        :rtype:     basestring
        """
        content_manager = manager_factory.content_manager()
        try:
            unit_id = content_manager.add_content_unit(unit.type_id, None, pulp_unit)
            self._added_count += 1
            return unit_id
        except DuplicateKeyError:
            logger.debug(_('cannot add unit; already exists. updating instead.'))
            return self._update_unit(unit, pulp_unit)

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
        content_manager = manager_factory.content_manager()

        try:
            content_manager.link_referenced_content_units(from_unit.type_id, from_unit.id, to_unit.type_id, [to_unit.id])

            if bidirectional:
                content_manager.link_referenced_content_units(to_unit.type_id, to_unit.id, from_unit.type_id, [from_unit.id])
        except Exception, e:
            logger.exception(_('Child link from parent [%(parent)s] to child [%(child)s] failed' %
                             {'parent': str(from_unit), 'child': str(to_unit)}))
            raise ImporterConduitException(e), None, sys.exc_info()[2]


class StatusMixin(object):

    def __init__(self, report_id, exception_class):
        self.report_id = report_id
        self.exception_class = exception_class
        self.progress_report = {}
        self.task_id = get_current_task_id()

    def set_progress(self, status):
        """
        Informs the server of the current state of the publish operation. The
        contents of the status is dependent on how the distributor
        implementation chooses to divide up the publish process.

        @param status: contains arbitrary data to describe the state of the
               publish; the contents may contain whatever information is relevant
               to the distributor implementation so long as it is serializable
        """

        if self.task_id is None:
            # not running within a task
            return

        try:
            self.progress_report[self.report_id] = status
            delta = {'progress_report': self.progress_report}
            TaskStatusManager.update_task_status(self.task_id, delta)
        except Exception, e:
            logger.exception('Exception from server setting progress for report [%s]' % self.report_id)
            try:
                logger.error('Progress value: %s' % str(status))
            except Exception:
                # Best effort to print this, but if its that grossly unserializable
                # the log will tank and we don't want that exception to bubble up
                pass
            raise self.exception_class(e), None, sys.exc_info()[2]


class PublishReportMixin(object):

    def build_success_report(self, summary, details):
        """
        Creates the PublishReport instance that needs to be returned to the Pulp
        server at the end of the publish_repo call.

        @param summary: short log of the publish; may be None but probably shouldn't be
        @type  summary: any serializable

        @param details: potentially longer log of the publish; may be None
        @type  details: any serializable
        """
        r = PublishReport(True, summary, details)
        return r

    def build_failure_report(self, summary, details):
        """
        Creates the PublishReport instance that needs to be returned to the Pulp
        server at the end of the publish_repo call. The report built in this
        fashion will indicate the publish operation has gracefully failed
        (as compared to an unexpected exception bubbling up).

        @param summary: short log of the publish; may be None but probably shouldn't be
        @type  summary: any serializable

        @param details: potentially longer log of the publish; may be None
        @type  details: any serializable
        """
        r = PublishReport(False, summary, details)
        return r

    def build_cancel_report(self, summary, details):
        """
        Creates the PublishReport instance that needs to be returned to the Pulp
        server at the end of the publish_repo call. The report built in this
        fashion will indicate the publish operation has been cancelled.

        @param summary: short log of the publish; may be None but probably shouldn't be
        @type  summary: any serializable

        @param details: potentially longer log of the publish; may be None
        @type  details: any serializable
        """
        r = PublishReport(False, summary, details)
        r.canceled_flag = True
        return r


def do_get_repo_units(repo_id, criteria, exception_class, as_generator=False):
    """
    Performs a repo unit association query. This is split apart so we can have
    custom mixins with different signatures.
    """
    try:
        association_query_manager = manager_factory.repo_unit_association_query_manager()
        # Use a get_units as_generator here and cast to a list later, if necessary.
        units = association_query_manager.get_units(repo_id, criteria=criteria, as_generator=True)

        # Load all type definitions so we don't hammer the database.
        type_defs = dict((t['id'], t) for t in types_db.all_type_definitions())

        # Transfer object generator.
        def _transfer_object_generator():
            for u in units:
                yield common_utils.to_plugin_associated_unit(u, type_defs[u['unit_type_id']])

        if as_generator:
            return _transfer_object_generator()

        # Maintain legacy behavior by default.
        return list(_transfer_object_generator())

    except Exception, e:
        logger.exception('Exception from server requesting all content units for repository [%s]' % repo_id)
        raise exception_class(e), None, sys.exc_info()[2]

