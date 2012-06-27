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
from pulp.server.managers import factory as managers
from pulp.plugins import loader as plugins
from pulp.plugins.profiler import Profiler
from pulp.plugins.conduits.profiler import ProfilerConduit
from pulp.server.exceptions import PulpExecutionException
from pulp.server.agent import PulpAgent
from logging import getLogger


_LOG = getLogger(__name__)


class AgentManager(object):
    """
    The agent manager.
    """

    def unregistered(self, id):
        """
        Notification that a consumer (agent) has
        been unregistered.  This ensure that all registration
        artifacts have been cleaned up.
        @param id: The consumer ID.
        @type id: str
        """
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(id)
        agent = PulpAgent(consumer)
        agent.consumer.unregistered()

    def bind(self, id, repo_id):
        """
        Apply a bind to the agent.
        @param repo_id: A repository ID.
        @type repo_id: str
        """
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(id)
        agent = PulpAgent(consumer)
        agent.consumer.bind(repo_id)

    def unbind(self, id, repo_id):
        """
        Apply a unbind to the agent.
        @param repo_id: A repository ID.
        @type repo_id: str
        """
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(id)
        agent = PulpAgent(consumer)
        agent.consumer.unbind(repo_id)

    def install_content(self, id, units, options):
        """
        Install content units on a consumer.
        @param id: The consumer ID.
        @type id: str
        @param units: A list of content units to be installed.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }
        @param options: Install options; based on unit type.
        @type options: dict
        """
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(id)
        conduit = ProfilerConduit()
        collated = Units(units)
        for typeid, units in collated.items():
            profiler, cfg = self.__profiler(typeid)
            units = profiler.install_units(id, units, options, cfg, conduit)
            collated[typeid] = units
        units = collated.join()
        agent = PulpAgent(consumer)
        agent.content.install(units, options)

    def update_content(self, id, units, options):
        """
        Update content units on a consumer.
        @param id: The consumer ID.
        @type id: str
        @param units: A list of content units to be updated.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }
        @param options: Update options; based on unit type.
        @type options: dict
        """
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(id)
        conduit = ProfilerConduit()
        collated = Units(units)
        for typeid, units in collated.items():
            profiler, cfg = self.__profiler(typeid)
            units = profiler.update_units(id, units, options, cfg, conduit)
            collated[typeid] = units
        units = collated.join()
        agent = PulpAgent(consumer)
        agent.content.update(units, options)

    def uninstall_content(self, id, units, options):
        """
        Uninstall content units on a consumer.
        @param id: The consumer ID.
        @type id: str
        @param units: A list of content units to be uninstalled.
        @type units: list of:
            { type_id:<str>, type_id:<dict> }
        @param options: Uninstall options; based on unit type.
        @type options: dict
        """
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(id)
        conduit = ProfilerConduit()
        collated = Units(units)
        for typeid, units in collated.items():
            profiler, cfg = self.__profiler(typeid)
            units = profiler.uninstall_units(id, units, options, cfg, conduit)
            collated[typeid] = units
        units = collated.join()
        agent = PulpAgent(consumer)
        agent.content.uninstall(units, options)

    def send_profile(self, id):
        """
        Send the content profile(s).
        @param id: The consumer ID.
        @type id: str
        """
        _LOG.info(id)

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
            plugin, cfg = plugins.get_profiler_by_type(typeid)
        except plugins.PluginNotFound:
            plugin = Profiler()
            cfg = {}
        return _Plugin(plugin), cfg


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


class _Plugin:
    """
    Plugin wrapper.
    Used to consistently wrap plugin method calls in a
    PulpExecutionException.
    """

    class Method:
        """
        Method wrapper.
        Used to consistently wrap plugin method calls in a
        PulpExecutionException.
        """
        
        def __init__(self, method):
            """
            @param method: method to be wrapped.
            @type method: instancemethod
            """
            self.__method = method
            
        def __call__(self, *args, **kwargs):
            try:
                return self.__method(*args, **kwargs)
            except Exception, e:
                msg = str(e)
                tb = sys.exc_info()[2]
                raise PulpExecutionException(msg), None, tb
    
    def __init__(self, plugin):
        """
        @param plugin: The plugin to be wrapped.
        @type plugin: Plugin
        """
        self.__plugin = plugin
        
    def __getattr__(self, name):
        attr = getattr(self.__plugin, name)
        if callable(attr):
            return self.Method(attr)
        else:
            return attr
