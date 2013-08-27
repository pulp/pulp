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
Profiler conduits.
"""
from gettext import gettext as _

import logging
import sys

from pulp.plugins.conduits.mixins import MultipleRepoUnitsMixin, ProfilerConduitException, UnitAssociationCriteria
from pulp.plugins.model import Unit
from pulp.plugins.types import database as types_db
from pulp.server.managers import factory as managers

_LOG = logging.getLogger(__name__)

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


    def get_repo_units(self, repo_id, content_type_id, additional_unit_fields=[]):
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
        try:
            # Get type definition and unit_key for given content type
            type_def = types_db.type_definition(content_type_id)
            unit_key_fields = type_def['unit_key']

            # Query repo association manager to get all units of given type
            # associated with given repo. Limit data by requesting only the fields
            # that are needed.
            query_manager = managers.repo_unit_association_query_manager()
            unit_fields = list(set(unit_key_fields + additional_unit_fields))
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
            _LOG.exception(_('Exception from server getting units from repo [%s]' % repo_id))
            raise self.exception_class(e), None, sys.exc_info()[2]
