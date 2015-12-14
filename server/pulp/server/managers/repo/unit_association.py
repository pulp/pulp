"""
Contains the manager class and exceptions for handling the mappings between
repositories and content units.
"""
from gettext import gettext as _
import logging
import sys

from celery import task
import mongoengine
import pymongo

from pulp.common import error_codes
from pulp.plugins.conduits.unit_import import ImportUnitConduit
from pulp.plugins.config import PluginCallConfiguration
from pulp.plugins.loader import api as plugin_api
from pulp.server.async.tasks import Task
from pulp.server.controllers import repository as repo_controller
from pulp.server.controllers import units as units_controller
from pulp.server.db import model
from pulp.server.db.model.criteria import UnitAssociationCriteria
from pulp.server.db.model.repository import RepoContentUnit
import pulp.plugins.conduits._common as conduit_common_utils
import pulp.server.exceptions as exceptions
import pulp.server.managers.factory as manager_factory


# Valid sort strings
SORT_TYPE_ID = 'type_id'
SORT_CREATED = 'created'
SORT_UPDATED = 'updated'

_VALID_SORTS = (SORT_TYPE_ID, SORT_CREATED, SORT_UPDATED)

SORT_ASCENDING = pymongo.ASCENDING
SORT_DESCENDING = pymongo.DESCENDING

_VALID_DIRECTIONS = (SORT_ASCENDING, SORT_DESCENDING)

logger = logging.getLogger(__name__)


class RepoUnitAssociationManager(object):
    """
    Manager used to handle the associations between repositories and content
    units. The functionality provided within assumes the repo and units have
    been created outside of this manager.
    """

    def associate_unit_by_id(self, repo_id, unit_type_id, unit_id, update_repo_metadata=True):
        """
        Creates an association between the given repository and content unit.

        If there is already an association between the given repo and content
        unit where all other metadata matches the input to this method,
        this call has no effect.

        Both repo and unit must exist in the database prior to this call,
        however this call will not verify that for performance reasons. Care
        should be taken by the caller to preserve the data integrity.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param unit_type_id: identifies the type of unit being added
        @type  unit_type_id: str

        @param unit_id: uniquely identifies the unit within the given type
        @type  unit_id: str

        @param update_repo_metadata: if True, updates the unit association count
                                  after the new association is made. The last
                                  unit added field will also be updated.  Set this
                                  to False when doing bulk associations, and
                                  make one call to update the count at the end.
                                  defaults to True
        @type  update_repo_metadata: bool

        @raise InvalidType: if the given owner type is not of the valid enumeration
        """

        # If the association already exists, no need to do anything else
        spec = {'repo_id': repo_id,
                'unit_id': unit_id,
                'unit_type_id': unit_type_id}
        existing_association = RepoContentUnit.get_collection().find_one(spec)
        if existing_association is not None:
            return

        similar_exists = False
        if update_repo_metadata:
            similar_exists = RepoUnitAssociationManager.association_exists(repo_id, unit_id,
                                                                           unit_type_id)

        # Create the database entry
        association = RepoContentUnit(repo_id, unit_id, unit_type_id)
        RepoContentUnit.get_collection().save(association)

        # update the count and times of associated units on the repo object
        if update_repo_metadata and not similar_exists:
            repo_controller.update_unit_count(repo_id, unit_type_id, 1)
            repo_controller.update_last_unit_added(repo_id)

    def associate_all_by_ids(self, repo_id, unit_type_id, unit_id_list):
        """
        Creates multiple associations between the given repo and content units.

        See associate_unit_by_id for semantics.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param unit_type_id: identifies the type of unit being added
        @type  unit_type_id: str

        @param unit_id_list: list or generator of unique identifiers for units within the given type
        @type  unit_id_list: list or generator of str

        :return:    number of new units added to the repo
        :rtype:     int

        @raise InvalidType: if the given owner type is not of the valid enumeration
        """

        # There may be a way to batch this in mongo which would be ideal for a
        # bulk operation like this. But for deadline purposes, this call will
        # simply loop and call the single method.

        unique_count = 0
        for unit_id in unit_id_list:
            if not RepoUnitAssociationManager.association_exists(repo_id, unit_id, unit_type_id):
                unique_count += 1
            self.associate_unit_by_id(repo_id, unit_type_id, unit_id, False)

        # update the count of associated units on the repo object
        if unique_count:
            repo_controller.update_unit_count(repo_id, unit_type_id, unique_count)
            repo_controller.update_last_unit_added(repo_id)
        return unique_count

    @staticmethod
    def _units_from_criteria(source_repo, criteria):
        """
        Given a criteria, return an iterator of units

        :param source_repo: repository to look for units in
        :type  source_repo: pulp.server.db.model.Repository
        :param criteria:    criteria object to use for the search parameters
        :type  criteria:    pulp.server.db.model.criteria.UnitAssociationCriteria

        :return:    generator of pulp.server.db.model.ContentUnit instances
        :rtype:     generator
        """
        association_q = mongoengine.Q(__raw__=criteria.association_spec)
        if criteria.type_ids:
            association_q &= mongoengine.Q(unit_type_id__in=criteria.type_ids)
        unit_q = mongoengine.Q(__raw__=criteria.unit_spec)
        return repo_controller.find_repo_content_units(
            repository=source_repo,
            repo_content_unit_q=association_q,
            units_q=unit_q,
            yield_content_unit=True)

    @classmethod
    def associate_from_repo(cls, source_repo_id, dest_repo_id, criteria=None,
                            import_config_override=None):
        """
        Creates associations in a repository based on the contents of a source
        repository. Units from the source repository can be filtered by
        specifying a criteria object.

        The destination repository must have an importer that can support
        the types of units being associated. This is done by analyzing the
        unit list and the importer metadata and takes place before the
        destination repository is called.

        Pulp does not actually perform the associations as part of this call.
        The unit list is determined and passed to the destination repository's
        importer. It is the job of the importer to make the associate calls
        back into Pulp where applicable.

        If criteria is None, the effect of this call is to copy the source
        repository's associations into the destination repository.

        :param source_repo_id:         identifies the source repository
        :type  source_repo_id:         str
        :param dest_repo_id:           identifies the destination repository
        :type  dest_repo_id:           str
        :param criteria:               optional; if specified, will filter the units retrieved from
                                       the source repository
        :type  criteria:               pulp.server.db.model.criteria.UnitAssociationCriteria
        :param import_config_override: optional config containing values to use for this import only
        :type  import_config_override: dict
        :return:                       dict with key 'units_successful' whose
                                       value is a list of unit keys that were copied.
                                       units that were associated by this operation
        :rtype:                        dict
        :raise MissingResource:        if either of the specified repositories don't exist
        """
        source_repo = model.Repository.objects.get_repo_or_missing_resource(source_repo_id)
        dest_repo = model.Repository.objects.get_repo_or_missing_resource(dest_repo_id)

        dest_repo_importer = model.Importer.objects.get_or_404(repo_id=dest_repo_id)
        source_repo_importer = model.Importer.objects.get_or_404(repo_id=source_repo_id)

        # The docs are incorrect on the list_importer_types call; it actually
        # returns a dict with the types under key "types" for some reason.
        supported_type_ids = set(plugin_api.list_importer_types(
            dest_repo_importer.importer_type_id)['types'])

        # Get the unit types from the repo source repo
        source_repo_unit_types = set(source_repo.content_unit_counts.keys())

        # Now we can make sure the destination repository's importer is capable
        # of importing either the selected units or all of the units
        if not source_repo_unit_types.issubset(supported_type_ids):
            raise exceptions.PulpCodedException(
                error_code=error_codes.PLP0000,
                message='The the target importer does not support the types from the source')

        transfer_units = None
        # If criteria is specified, retrieve the list of units now
        if criteria is not None:
            # if all source types have been converted to mongo - search via new style
            if source_repo_unit_types.issubset(set(plugin_api.list_unit_models())):
                transfer_units = cls._units_from_criteria(source_repo, criteria)
            else:
                # else, search via old style
                associate_us = load_associated_units(source_repo_id, criteria)
                # If units were supposed to be filtered but none matched, we're done
                if len(associate_us) == 0:
                    # Return an empty list to indicate nothing was copied
                    return {'units_successful': []}
                # Convert all of the units into the plugin standard representation if
                # a filter was specified
                transfer_units = None
                if associate_us is not None:
                    transfer_units = create_transfer_units(associate_us)

        # Convert the two repos into the plugin API model
        transfer_dest_repo = dest_repo.to_transfer_repo()
        transfer_source_repo = source_repo.to_transfer_repo()

        # Invoke the importer
        importer_instance, plugin_config = plugin_api.get_importer_by_id(
            dest_repo_importer.importer_type_id)

        call_config = PluginCallConfiguration(plugin_config, dest_repo_importer.config,
                                              import_config_override)
        conduit = ImportUnitConduit(
            source_repo_id, dest_repo_id, source_repo_importer.importer_type_id,
            dest_repo_importer.importer_type_id)

        try:
            copied_units = importer_instance.import_units(
                transfer_source_repo, transfer_dest_repo, conduit, call_config,
                units=transfer_units)

            unit_ids = [u.to_id_dict() for u in copied_units]
            repo_controller.rebuild_content_unit_counts(dest_repo)
            return {'units_successful': unit_ids}
        except Exception:
            msg = _('Exception from importer [%(i)s] while importing units into repository [%(r)s]')
            msg_dict = {'i': dest_repo_importer.importer_type_id, 'r': dest_repo_id}
            logger.exception(msg % msg_dict)
            raise exceptions.PulpExecutionException(), None, sys.exc_info()[2]

    def unassociate_unit_by_id(self, repo_id, unit_type_id, unit_id, notify_plugins=True):
        """
        Removes the association between a repo and the given unit. Only the
        association made by the given owner will be removed. It is possible the
        repo will still have a manually created association will for the unit.

        If no association exists between the repo and unit, this call has no
        effect.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param unit_type_id: identifies the type of unit being removed
        @type  unit_type_id: str

        @param unit_id: uniquely identifies the unit within the given type
        @type  unit_id: str

        @param notify_plugins: if true, relevant plugins will be informed of the
               removal
        @type  notify_plugins: bool
        """
        return self.unassociate_all_by_ids(repo_id, unit_type_id, [unit_id],
                                           notify_plugins=notify_plugins)

    def unassociate_all_by_ids(self, repo_id, unit_type_id, unit_id_list,
                               notify_plugins=True):
        """
        Removes the association between a repo and a number of units. Only the
        association made by the given owner will be removed. It is possible the
        repo will still have a manually created association will for the unit.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param unit_type_id: identifies the type of units being removed
        @type  unit_type_id: str

        @param unit_id_list: list of unique identifiers for units within the given type
        @type  unit_id_list: list of str

        @param notify_plugins: if true, relevant plugins will be informed of the
               removal
        @type  notify_plugins: bool
        """
        association_filters = {'unit_id': {'$in': unit_id_list}}
        criteria = UnitAssociationCriteria(type_ids=[unit_type_id],
                                           association_filters=association_filters)

        return self.unassociate_by_criteria(repo_id, criteria,
                                            notify_plugins=notify_plugins)

    @staticmethod
    def unassociate_by_criteria(repo_id, criteria, notify_plugins=True):
        """
        Unassociate units that are matched by the given criteria.

        :param repo_id:        identifies the repo
        :type  repo_id:        str
        :param criteria:
        :param notify_plugins: if true, relevant plugins will be informed of the removal
        :type  notify_plugins: bool
        """
        association_query_manager = manager_factory.repo_unit_association_query_manager()
        unassociate_units = association_query_manager.get_units(repo_id, criteria=criteria)

        if len(unassociate_units) == 0:
            return {}

        unit_map = {}  # maps unit_type_id to a list of unit_ids

        for unit in unassociate_units:
            id_list = unit_map.setdefault(unit['unit_type_id'], [])
            id_list.append(unit['unit_id'])

        collection = RepoContentUnit.get_collection()

        for unit_type_id, unit_ids in unit_map.items():
            spec = {'repo_id': repo_id,
                    'unit_type_id': unit_type_id,
                    'unit_id': {'$in': unit_ids}
                    }
            collection.remove(spec)

            unique_count = sum(
                1 for unit_id in unit_ids if not RepoUnitAssociationManager.association_exists(
                    repo_id, unit_id, unit_type_id))
            if not unique_count:
                continue

            repo_controller.update_unit_count(repo_id, unit_type_id, -unique_count)

        repo_controller.update_last_unit_removed(repo_id)

        # Convert the units into transfer units. This happens regardless of whether or not
        # the plugin will be notified as it's used to generate the return result,
        transfer_units = create_transfer_units(unassociate_units)

        if notify_plugins:
            remove_from_importer(repo_id, transfer_units)

        # Match the return type/format as copy
        serializable_units = [u.to_id_dict() for u in transfer_units]

        return {'units_successful': serializable_units}

    @staticmethod
    def association_exists(repo_id, unit_id, unit_type_id):
        """
        Determines if an identical association already exists.

        I know the order of arguments does not match other methods in this
        module, but it does match the constructor for the RepoContentUnit
        object, which I think is the higher authority.

        @param repo_id: identifies the repo
        @type  repo_id: str

        @param unit_type_id: identifies the type of unit being removed
        @type  unit_type_id: str

        @param unit_id: uniquely identifies the unit within the given type
        @type  unit_id: str

        @return: True if unique else False
        @rtype:  bool
        """
        spec = {
            'repo_id': repo_id,
            'unit_id': unit_id,
            'unit_type_id': unit_type_id,
        }
        unit_coll = RepoContentUnit.get_collection()

        existing_count = unit_coll.find(spec).count()
        return bool(existing_count)


associate_from_repo = task(RepoUnitAssociationManager.associate_from_repo, base=Task)
unassociate_by_criteria = task(RepoUnitAssociationManager.unassociate_by_criteria, base=Task)


def load_associated_units(source_repo_id, criteria):
    criteria.association_fields = None

    # Retrieve the units to be associated
    association_query_manager = manager_factory.repo_unit_association_query_manager()
    associate_us = association_query_manager.get_units(source_repo_id, criteria=criteria)

    return associate_us


def create_transfer_units(associate_units):
    unit_key_fields = {}

    transfer_units = []
    for unit in associate_units:
        type_id = unit['unit_type_id']
        if type_id not in unit_key_fields:
            unit_key_fields[type_id] = units_controller.get_unit_key_fields_for_type(type_id)
        u = conduit_common_utils.to_plugin_associated_unit(unit, type_id, unit_key_fields[type_id])
        transfer_units.append(u)

    return transfer_units


def remove_from_importer(repo_id, transfer_units):
    repo_obj = model.Repository.objects.get_repo_or_missing_resource(repo_id)
    transfer_repo = repo_obj.to_transfer_repo()
    repo_importer = model.Importer.objects(repo_id=repo_id).first()

    # Retrieve the plugin instance to invoke
    importer_instance, plugin_config = plugin_api.get_importer_by_id(
        repo_importer.importer_type_id)
    call_config = PluginCallConfiguration(plugin_config, repo_importer.config)

    # Invoke the importer's remove method
    try:
        importer_instance.remove_units(transfer_repo, transfer_units, call_config)
    except Exception:
        msg = _('Exception from importer [%(i)s] while removing units from repo [%(r)s]')
        msg = msg % {'i': repo_importer.importer_type_id, 'r': repo_id}
        logger.exception(msg)

        # Do not raise the exception; this should not block the removal and is
        # intended to be more informational to the plugin rather than a requirement
