"""
Profiler conduits.
"""
from gettext import gettext as _
import logging
import sys

from pulp.plugins.conduits.mixins import MultipleRepoUnitsMixin, ProfilerConduitException
from pulp.plugins.model import Unit
from pulp.server.controllers import units as units_controller
from pulp.server.db.model.criteria import UnitAssociationCriteria
from pulp.server.managers import factory as managers


_logger = logging.getLogger(__name__)


class ProfilerConduit(MultipleRepoUnitsMixin):

    def __init__(self):
        MultipleRepoUnitsMixin.__init__(self, ProfilerConduitException)

    def get_bindings(self, consumer_id):
        """
        Get a list of bound repository IDs.

        @param consumer_id: A consumer ID.
        @type consumer_id: str

        @return: A list of bound repository IDs.
        @rtype: list
        """
        manager = managers.consumer_bind_manager()
        bindings = manager.find_by_consumer(consumer_id)
        return [b['repo_id'] for b in bindings]

    def get_repo_units(self, repo_id, content_type_id, additional_unit_fields=None):
        """
        Searches for units in the given repository with given content type
        and returns a plugin unit containing unit id, unit key and any additional
        fields requested.

        :param repo_id: repo id
        :type  repo_id: str

        :param content_type_id: content type id of the units
        :type  content_type_id: str

        :param additional_unit_fields: additional fields from the unit metadata to be added
                                       in the result
        :type additional_unit_fields: list of str

        :return: list of unit instances
        :rtype:  list of pulp.plugins.model.Unit
        """
        additional_unit_fields = additional_unit_fields or []
        try:
            unit_key_fields = units_controller.get_unit_key_fields_for_type(content_type_id)

            # Query repo association manager to get all units of given type
            # associated with given repo. Limit data by requesting only the fields
            # that are needed.
            query_manager = managers.repo_unit_association_query_manager()
            unit_fields = list(unit_key_fields) + list(additional_unit_fields)
            criteria = UnitAssociationCriteria(association_fields=['unit_id'],
                                               unit_fields=unit_fields)
            units = query_manager.get_units_by_type(repo_id, content_type_id, criteria)

            # Convert units to plugin units with unit_key and required metadata values for each unit
            all_units = []
            for unit in units:
                unit_key = {}
                metadata = {}
                for k in unit_key_fields:
                    unit_key[k] = unit['metadata'].pop(k)
                # Add unit_id and any additional unit fields requested by plugins
                metadata['unit_id'] = unit.pop('unit_id')
                for field in additional_unit_fields:
                    metadata[field] = unit['metadata'].pop(field, None)

                u = Unit(content_type_id, unit_key, metadata, None)
                all_units.append(u)

            return all_units

        except Exception, e:
            _logger.exception(_('Exception from server getting units from repo [%s]' % repo_id))
            raise self.exception_class(e), None, sys.exc_info()[2]
