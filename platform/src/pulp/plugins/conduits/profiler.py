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

from pulp.server.managers import factory as managers
from pulp.plugins.conduits import _common
from pulp.plugins.types import database as typedb
from pulp.plugins.conduits.mixins import ProfilerConduitException

_LOG = logging.getLogger(__name__)


class ProfilerConduit(object):

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

    def get_units(self, repo_id, criteria=None):
        """
        Returns the collection of content units associated with the
        specified repository IDs.

        @param repo_id: A repo ID.
        @type repo_id: str

        @param criteria: used to scope the returned results or the data within
        @type  criteria: L{Criteria}

        @return: list of unit instances
        @rtype:  list of L{AssociatedUnit}
        """
        try:
            result = []
            manager = managers.repo_unit_association_query_manager()
            units = manager.get_units_across_types(repo_id, criteria=criteria)
            typedefs = dict([(u['unit_type_id'], None) for u in units])
            for type_id in typedefs.keys():
                typedefs[type_id] = typedb.type_definition(type_id)
            for unit in units:
                type_id = unit['unit_type_id']
                u = _common.to_plugin_unit(unit, typedefs[type_id])
                result.append(u)
            return result
        except Exception, e:
            _LOG.exception('Error getting units for repository [%s]' % repo_id)
            raise ProfilerConduitException(e), None, sys.exc_info()[2]

