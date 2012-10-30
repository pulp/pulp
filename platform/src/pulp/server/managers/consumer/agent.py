#!/usr/bin/python
#
# Copyright (c) 2012 Red Hat, Inc.
#
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
Contains agent management classes
"""

import sys

from logging import getLogger

from pulp.server.dispatch import factory
from pulp.server.managers import factory as managers
from pulp.plugins.loader import api as plugin_api
from pulp.plugins.loader import exceptions as plugin_exceptions
from pulp.plugins.profiler import Profiler, InvalidUnitsRequested
from pulp.plugins.conduits.profiler import ProfilerConduit
from pulp.plugins.model import Consumer as ProfiledConsumer
from pulp.server.exceptions import PulpExecutionException, PulpDataException
from pulp.server.compat import json, json_util
from pulp.server.agent import PulpAgent


_LOG = getLogger(__name__)


class AgentManager(object):
    """
    The agent manager.
    """

    def unregistered(self, consumer_id):
        """
        Notification that a consumer (agent) has
        been unregistered.  This ensure that all registration
        artifacts have been cleaned up.
        @param consumer_id: The consumer ID.
        @type consumer_id: str
        """
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(consumer_id)
        agent = PulpAgent(consumer)
        agent.consumer.unregistered()

    def bind(self, consumer_id, repo_id, distributor_id, options):
        """
        Apply a bind to the agent.
        @param consumer_id: The consumer ID.
        @type consumer_id: str
        @param repo_id: A repository ID.
        @type repo_id: str
        @param distributor_id: A distributor ID.
        @type distributor_id: str
        @param options: The options are handler specific.
        @type options: dict
        """
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(consumer_id)
        binding = dict(repo_id=repo_id, distributor_id=distributor_id)
        definitions = self.__definitions([binding])
        agent = PulpAgent(consumer)
        agent.consumer.bind(definitions, options)
        # request tracking
        manager = managers.consumer_bind_manager()
        request_id = factory.context().call_request_id
        manager.request_pending(consumer_id, repo_id, distributor_id, request_id)

    def unbind(self, consumer_id, repo_id, distributor_id, options):
        """
        Apply a unbind to the agent.
        @param consumer_id: The consumer ID.
        @type consumer_id: str
        @param repo_id: A repository ID.
        @type repo_id: str
        @param distributor_id: A distributor ID.
        @type distributor_id: str
        @param options: The options are handler specific.
        @type options: dict
        """
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(consumer_id)
        agent = PulpAgent(consumer)
        agent.consumer.unbind(repo_id, options)
        manager = managers.consumer_bind_manager()
        request_id = factory.context().call_request_id
        manager.request_pending(consumer_id, repo_id, distributor_id, request_id)

    def install_content(self, consumer_id, units, options):
        """
        Install content units on a consumer.
        @param consumer_id: The consumer ID.
        @type consumer_id: str
        @param units: A list of content units to be installed.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }
        @param options: Install options; based on unit type.
        @type options: dict
        """
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(consumer_id)
        conduit = ProfilerConduit()
        collated = Units(units)
        for typeid, units in collated.items():
            pc = self.__profiled_consumer(consumer_id)
            profiler, cfg = self.__profiler(typeid)
            units = self.__invoke_plugin(
                profiler.install_units,
                pc,
                units,
                options,
                cfg,
                conduit)
            collated[typeid] = units
        units = collated.join()
        agent = PulpAgent(consumer)
        agent.content.install(units, options)

    def update_content(self, consumer_id, units, options):
        """
        Update content units on a consumer.
        @param consumer_id: The consumer ID.
        @type consumer_id: str
        @param units: A list of content units to be updated.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }
        @param options: Update options; based on unit type.
        @type options: dict
        """
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(consumer_id)
        conduit = ProfilerConduit()
        collated = Units(units)
        for typeid, units in collated.items():
            pc = self.__profiled_consumer(consumer_id)
            profiler, cfg = self.__profiler(typeid)
            units = self.__invoke_plugin(
                profiler.update_units,
                pc,
                units,
                options,
                cfg,
                conduit)
            collated[typeid] = units
        units = collated.join()
        agent = PulpAgent(consumer)
        agent.content.update(units, options)

    def uninstall_content(self, consumer_id, units, options):
        """
        Uninstall content units on a consumer.
        @param consumer_id: The consumer ID.
        @type consumer_id: str
        @param units: A list of content units to be uninstalled.
        @type units: list of:
            { type_id:<str>, type_id:<dict> }
        @param options: Uninstall options; based on unit type.
        @type options: dict
        """
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(consumer_id)
        conduit = ProfilerConduit()
        collated = Units(units)
        for typeid, units in collated.items():
            pc = self.__profiled_consumer(consumer_id)
            profiler, cfg = self.__profiler(typeid)
            units = self.__invoke_plugin(
                profiler.uninstall_units,
                pc,
                units,
                options,
                cfg,
                conduit)
            collated[typeid] = units
        units = collated.join()
        agent = PulpAgent(consumer)
        agent.content.uninstall(units, options)

    def send_profile(self, consumer_id):
        """
        Send the content profile(s).
        @param consumer_id: The consumer ID.
        @type consumer_id: str
        """
        _LOG.info(consumer_id)

    def __invoke_plugin(self, call, *args, **kwargs):
        try:
            return call(*args, **kwargs)
        except InvalidUnitsRequested, e:
            raise PulpDataException(e.units, e.message)
        except Exception:
            raise PulpExecutionException(), None, sys.exc_info()[2]

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
        return plugin, cfg

    def __profiled_consumer(self, consumer_id):
        """
        Get a profiler consumer model object.
        @param id: A consumer ID.
        @type id: str
        @return: A populated profiler consumer model object.
        @rtype: L{ProfiledConsumer}
        """
        profiles = {}
        manager = managers.consumer_profile_manager()
        for p in manager.get_profiles(consumer_id):
            typeid = p['content_type']
            profile = p['profile']
            profiles[typeid] = profile
        return ProfiledConsumer(consumer_id, profiles)

    def __definitions(self, bindings):
        """
        Build the bind definitions needed by the agent.
        @param bindings: A list of bindings.
          Each binding is:
            {consumer_id:<str>, repo_id:<str>, distributor_id:<str>}
        @type bindings: list
        @return A list of bind definitions.
        @rtype: list
        """
        definitions = []
        for binding in bindings:
            manager = managers.repo_query_manager()
            repository = manager.get_repository(binding['repo_id'])
            manager = managers.repo_distributor_manager()
            distributor = manager.get_distributor(
                binding['repo_id'],
                binding['distributor_id'])
            details = manager.create_bind_payload(
                binding['repo_id'],
                binding['distributor_id'])
            definition = dict(
                type_id=distributor['distributor_type_id'],
                repository=repository,
                details=details)
            definitions.append(definition)
        definitions = json.loads(json.dumps(definitions, default=json_util.default))
        return definitions


class Units(dict):
    """
    Collated content units
    """

    def __init__(self, units):
        """
        Unit is: {type_id:<str>, unit_key:<dict>}
        @param units: A list of content units.
        @type units: list
        """
        for unit in units:
            typeid = unit['type_id']
            lst = self.get(typeid)
            if lst is None:
                lst = []
                self[typeid] = lst
            lst.append(unit)

    def join(self):
        """
        Flat (uncollated) list of units.
        @return: A list of units.
        @rtype: list
        """
        return [j for i in self.values() for j in i]
