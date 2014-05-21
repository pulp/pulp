# Copyright (c) 2012 Red Hat, Inc.
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
from uuid import uuid4

from pulp.common import constants
from pulp.common import tags
from pulp.plugins.conduits.profiler import ProfilerConduit
from pulp.plugins.loader import api as plugin_api
from pulp.plugins.loader import exceptions as plugin_exceptions
from pulp.plugins.model import Consumer as ProfiledConsumer
from pulp.plugins.profiler import Profiler, InvalidUnitsRequested
from pulp.server.agent import PulpAgent
from pulp.server.db.model.consumer import Bind
from pulp.server.exceptions import PulpExecutionException, PulpDataException, MissingResource
from pulp.server.managers import factory as managers
from pulp.server.async.task_status_manager import TaskStatusManager
from pulp.server.agent import Context


logger = getLogger(__name__)


class AgentManager(object):
    """
    The agent manager.
    """

    def unregistered(self, consumer_id):
        """
        Notification that a consumer (agent) has
        been unregistered.  This ensure that all registration
        artifacts have been cleaned up.
        :param consumer_id: The consumer ID.
        :type consumer_id: str
        """
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(consumer_id)
        context = Context(consumer)
        agent = PulpAgent()
        agent.consumer.unregistered(context)

    @staticmethod
    def bind(consumer_id, repo_id, distributor_id, options):
        """
        Request the agent to perform the specified bind. This method will be called
        after the server-side representation of the binding has been created.

        :param consumer_id: The consumer ID.
        :type consumer_id: str
        :param repo_id: A repository ID.
        :type repo_id: str
        :param distributor_id: A distributor ID.
        :type distributor_id: str
        :param options: The options are handler specific.
        :type options: dict
        :return: The task created by the bind
        :rtype: dict
        """
        # track agent operations using a pseudo task
        task_id = str(uuid4())
        task_tags = [
            tags.resource_tag(tags.RESOURCE_CONSUMER_TYPE, consumer_id),
            tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
            tags.resource_tag(tags.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
            tags.action_tag(tags.ACTION_AGENT_BIND)
        ]
        task = TaskStatusManager.create_task_status(task_id, 'agent', tags=task_tags)

        # agent request
        consumer_manager = managers.consumer_manager()
        binding_manager = managers.consumer_bind_manager()
        consumer = consumer_manager.get_consumer(consumer_id)
        binding = binding_manager.get_bind(consumer_id, repo_id, distributor_id)
        agent_bindings = AgentManager._bindings([binding])
        context = Context(
            consumer,
            task_id=task_id,
            action='bind',
            consumer_id=consumer_id,
            repo_id=repo_id,
            distributor_id=distributor_id)
        agent = PulpAgent()
        agent.consumer.bind(context, agent_bindings, options)

        # bind action tracking
        consumer_manager = managers.consumer_bind_manager()
        consumer_manager.action_pending(
            consumer_id,
            repo_id,
            distributor_id,
            Bind.Action.BIND,
            task_id)

        return task

    @staticmethod
    def unbind(consumer_id, repo_id, distributor_id, options):
        """
        Request the agent to perform the specified unbind.
        :param consumer_id: The consumer ID.
        :type consumer_id: str
        :param repo_id: A repository ID.
        :type repo_id: str
        :param distributor_id: A distributor ID.
        :type distributor_id: str
        :param options: The options are handler specific.
        :type options: dict
        :return: A task ID that may be used to track the agent request.
        :rtype: str
        """
        # track agent operations using a pseudo task
        task_id = str(uuid4())
        task_tags = [
            tags.resource_tag(tags.RESOURCE_CONSUMER_TYPE, consumer_id),
            tags.resource_tag(tags.RESOURCE_REPOSITORY_TYPE, repo_id),
            tags.resource_tag(tags.RESOURCE_REPOSITORY_DISTRIBUTOR_TYPE, distributor_id),
            tags.action_tag(tags.ACTION_AGENT_UNBIND)
        ]
        task = TaskStatusManager.create_task_status(task_id, 'agent', tags=task_tags)

        # agent request
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(consumer_id)
        binding = dict(repo_id=repo_id, distributor_id=distributor_id)
        bindings = AgentManager._unbindings([binding])
        context = Context(
            consumer,
            task_id=task_id,
            action='unbind',
            consumer_id=consumer_id,
            repo_id=repo_id,
            distributor_id=distributor_id)
        agent = PulpAgent()
        agent.consumer.unbind(context, bindings, options)

        # unbind action tracking
        manager = managers.consumer_bind_manager()
        manager.action_pending(
            consumer_id,
            repo_id,
            distributor_id,
            Bind.Action.UNBIND,
            task_id)

        return task

    @staticmethod
    def install_content(consumer_id, units, options):
        """
        Install content units on a consumer.
        :param consumer_id: The consumer ID.
        :type consumer_id: str
        :param units: A list of content units to be installed.
        :type units: list of:
            { type_id:<str>, unit_key:<dict> }
        :param options: Install options; based on unit type.
        :type options: dict
        :return: A task used to track the agent request.
        :rtype: dict
        """
        # track agent operations using a pseudo task
        task_id = str(uuid4())
        task_tags = [
            tags.resource_tag(tags.RESOURCE_CONSUMER_TYPE, consumer_id),
            tags.action_tag(tags.ACTION_AGENT_UNIT_INSTALL)
        ]
        task = TaskStatusManager.create_task_status(task_id, 'agent', tags=task_tags)

        # agent request
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(consumer_id)
        conduit = ProfilerConduit()
        collated = Units(units)
        for typeid, units in collated.items():
            pc = AgentManager._profiled_consumer(consumer_id)
            profiler, cfg = AgentManager._profiler(typeid)
            units = AgentManager._invoke_plugin(
                profiler.install_units,
                pc,
                units,
                options,
                cfg,
                conduit)
            collated[typeid] = units
        units = collated.join()
        context = Context(consumer, task_id=task_id, consumer_id=consumer_id)
        agent = PulpAgent()
        agent.content.install(context, units, options)
        return task

    @staticmethod
    def update_content(consumer_id, units, options):
        """
        Update content units on a consumer.
        :param consumer_id: The consumer ID.
        :type consumer_id: str
        :param units: A list of content units to be updated.
        :type units: list of:
            { type_id:<str>, unit_key:<dict> }
        :param options: Update options; based on unit type.
        :type options: dict
        :return: A task used to track the agent request.
        :rtype: dict
        """
        # track agent operations using a pseudo task
        task_id = str(uuid4())
        task_tags = [
            tags.resource_tag(tags.RESOURCE_CONSUMER_TYPE, consumer_id),
            tags.action_tag(tags.ACTION_AGENT_UNIT_UPDATE)
        ]
        task = TaskStatusManager.create_task_status(task_id, 'agent', tags=task_tags)

        # agent request
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(consumer_id)
        conduit = ProfilerConduit()
        collated = Units(units)
        for typeid, units in collated.items():
            pc = AgentManager._profiled_consumer(consumer_id)
            profiler, cfg = AgentManager._profiler(typeid)
            units = AgentManager._invoke_plugin(
                profiler.update_units,
                pc,
                units,
                options,
                cfg,
                conduit)
            collated[typeid] = units
        units = collated.join()
        context = Context(consumer, task_id=task_id, consumer_id=consumer_id)
        agent = PulpAgent()
        agent.content.update(context, units, options)
        return task

    @staticmethod
    def uninstall_content(consumer_id, units, options):
        """
        Uninstall content units on a consumer.
        :param consumer_id: The consumer ID.
        :type consumer_id: str
        :param units: A list of content units to be uninstalled.
        :type units: list of:
            { type_id:<str>, type_id:<dict> }
        :param options: Uninstall options; based on unit type.
        :type options: dict
        :return: A task ID that may be used to track the agent request.
        :rtype: dict
        """
        # track agent operations using a pseudo task
        task_id = str(uuid4())
        task_tags = [
            tags.resource_tag(tags.RESOURCE_CONSUMER_TYPE, consumer_id),
            tags.action_tag(tags.ACTION_AGENT_UNIT_UNINSTALL)
        ]
        task = TaskStatusManager.create_task_status(task_id, 'agent', tags=task_tags)

        # agent request
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(consumer_id)
        conduit = ProfilerConduit()
        collated = Units(units)
        for typeid, units in collated.items():
            pc = AgentManager._profiled_consumer(consumer_id)
            profiler, cfg = AgentManager._profiler(typeid)
            units = AgentManager._invoke_plugin(
                profiler.uninstall_units,
                pc,
                units,
                options,
                cfg,
                conduit)
            collated[typeid] = units
        units = collated.join()
        context = Context(consumer, task_id=task_id, consumer_id=consumer_id)
        agent = PulpAgent()
        agent.content.uninstall(context, units, options)
        return task

    def cancel_request(self, consumer_id, task_id):
        """
        Cancel an agent request associated with the specified task ID.
        :param consumer_id: The consumer ID.
        :type consumer_id: str
        :param: task_id: The task ID associated with the request.
        :type: str
        """
        manager = managers.consumer_manager()
        consumer = manager.get_consumer(consumer_id)
        context = Context(consumer)
        agent = PulpAgent()
        agent.cancel(context, task_id)

    @staticmethod
    def _invoke_plugin(call, *args, **kwargs):
        try:
            return call(*args, **kwargs)
        except InvalidUnitsRequested, e:
            trace = sys.exc_info()[2]
            raise PulpDataException(e.message), None, trace
        except Exception:
            raise PulpExecutionException(), None, sys.exc_info()[2]

    @staticmethod
    def _profiler(typeid):
        """
        Find the profiler.
        Returns the Profiler base class when not matched.
        :param typeid: The content type ID.
        :type typeid: str
        :return: (profiler, cfg)
        :rtype: tuple
        """
        try:
            plugin, cfg = plugin_api.get_profiler_by_type(typeid)
        except plugin_exceptions.PluginNotFound:
            plugin = Profiler()
            cfg = {}
        return plugin, cfg

    @staticmethod
    def _profiled_consumer(consumer_id):
        """
        Get a profiler consumer model object.

        :param consumer_id: A consumer ID.
        :type  consumer_id: str
        :return: A populated profiler consumer model object.
        :rtype:  pulp.plugins.model.Consumer
        """
        profiles = {}
        manager = managers.consumer_profile_manager()
        for p in manager.get_profiles(consumer_id):
            typeid = p['content_type']
            profile = p['profile']
            profiles[typeid] = profile
        return ProfiledConsumer(consumer_id, profiles)

    @staticmethod
    def _bindings(bindings):
        """
        Build the bindings needed by the agent. The returned bindings will be
        the payload created by the appropriate distributor.

        :param bindings: a list of binding object retrieved from the database
        :type  bindings: list
        :return: list of binding objects to send to the agent
        :rtype: list
        """
        agent_bindings = []
        for binding in bindings:
            repo_id = binding['repo_id']
            manager = managers.repo_distributor_manager()
            distributor = manager.get_distributor(
                binding['repo_id'],
                binding['distributor_id'])
            details = manager.create_bind_payload(
                binding['repo_id'],
                binding['distributor_id'],
                binding['binding_config'])
            type_id = distributor['distributor_type_id']
            agent_binding = dict(type_id=type_id, repo_id=repo_id, details=details)
            agent_bindings.append(agent_binding)
        return agent_bindings

    @staticmethod
    def _unbindings(bindings):
        """
        Build the (un)bindings needed by the agent.
        :param bindings: A list of binding IDs.
          Each binding is:
            {consumer_id:<str>, repo_id:<str>, distributor_id:<str>}
        :type bindings: list
        :return: A list of agent bindings.
          Each unbinding is: {type_id:<str>, repo_id:<str>}
        :rtype: list
        """
        agent_bindings = []
        for binding in bindings:
            manager = managers.repo_distributor_manager()
            try:
                distributor = manager.get_distributor(
                    binding['repo_id'],
                    binding['distributor_id'])
                type_id = distributor['distributor_type_id']
            except MissingResource:
                # In case the distributor was already deleted from the server.
                type_id = None
            agent_binding = dict(type_id=type_id, repo_id=binding['repo_id'])
            agent_bindings.append(agent_binding)
        return agent_bindings


class Units(dict):
    """
    Collated content units
    """

    def __init__(self, units):
        """
        Unit is: {type_id:<str>, unit_key:<dict>}
        :param units: A list of content units.
        :type units: list
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
        :return: A list of units.
        :rtype: list
        """
        return [j for i in self.values() for j in i]
