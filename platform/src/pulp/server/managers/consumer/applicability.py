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
Contains content applicability management classes
"""

from pulp.server.managers import factory as managers
from pulp.server.managers.pluginwrapper import PluginWrapper
from pulp.plugins.profiler import Profiler
from pulp.plugins.model import ApplicabilityReport
from pulp.plugins.model import Consumer as ProfiledConsumer
from pulp.plugins.conduits.profiler import ProfilerConduit
from pulp.plugins.loader import api as plugin_api
from pulp.plugins.loader import exceptions as plugin_exceptions
from logging import getLogger

_LOG = getLogger(__name__)


class ApplicabilityManager(object):

    def units_applicable(self, criteria, units):
        """
        Detemine and report which of the specified content units
        is applicable to consumers specified by the I{criteria}.
        @param criteria: The consumer selection criteria.
        @type criteria: list
        @param units: A list of content units to be installed.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }
        @return: A dict:
            {consumer_id:[<ApplicabilityReport>]}
        @rtype: list
        """
        result = {}
        conduit = ProfilerConduit()
        manager = managers.consumer_query_manager()
        ids = [c['id'] for c in manager.find_by_criteria(criteria)]
        manager = managers.consumer_profile_manager()
        profiles = manager.find_profiles(ids)
        for id in ids:
            for unit in units:
                typeid = unit['type_id']
                profiler, cfg = self.__profiler(typeid)
                pc = self.__profiled_consumer(id)
                report = profiler.unit_applicable(pc, unit, cfg, conduit)
                report.unit = unit
                ulist = result.setdefault(id, [])
                ulist.append(report)
        return result

    def __profiler(self, typeid):
        """
        Find the profiler.
        Returns the Profiler base class when not matched.
        @param typeid: The content type ID.
        @type typeid: str
        @return: (profiler, cfg)
        @rtype: tuple
        """
        try:
            plugin, cfg = plugin_api.get_profiler_by_type(typeid)
        except plugin_exceptions.PluginNotFound:
            plugin = Profiler()
            cfg = {}
        return PluginWrapper(plugin), cfg

    def __profiled_consumer(self, id):
        """
        Get a profiler consumer model object.
        @param id: A consumer ID.
        @type id: str
        @return: A populated profiler consumer model object.
        @rtype: L{ProfiledConsumer}
        """
        profiles = {}
        manager = managers.consumer_profile_manager()
        for p in manager.get_profiles(id):
            typeid = p['content_type']
            profile = p['profile']
            profiles[typeid] = profile
        return ProfiledConsumer(id, profiles)
