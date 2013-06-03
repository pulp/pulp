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
from pulp.plugins.conduits.mixins import MultipleRepoUnitsMixin
from pulp.plugins.conduits.mixins import ProfilerConduitException

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

    def search_unit_ids(self, type_id, criteria):
        """
        Searches for units of a given type in the server, regardless of their
        associations to any repositories and returns a list of unit ids.

        @param type_id: indicates the type of units being retrieved
        @type  type_id: str
        @param criteria: used to query which units are returned
        @type  criteria: pulp.server.db.model.criteria.Criteria

        @return: list of unit ids
        @rtype:  list of str
        """
        try:
            query_manager = managers.content_query_manager()
            criteria["fields"] = ['_id']
            units = query_manager.find_by_criteria(type_id, criteria)
            unit_ids = [u['_id'] for u in units] 
            return unit_ids

        except Exception, e:
            _LOG.exception(_('Exception from server searching units of type [%s]' % type_id))
            raise self.exception_class(e), None, sys.exc_info()[2]
