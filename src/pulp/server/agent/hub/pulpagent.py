# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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
Contains (proxy) classes that represent the pulp agent.
"""

from pulp.server.agent.hub.rest import Rest
from pulp.server.agent.hub.client import Agent
from pulp.server.agent.context import Context, Capability
from logging import getLogger


log = getLogger(__name__)


#
# Agent
#

class PulpAgent:
    """
    Represents a remote pulp agent.
    """

    def __init__(self, consumer):
        context = Context(consumer)
        # replyto
        context.replyto = dict(
            systemid='pulp',
            method='POST',
            path='/v2/agent/%s/reply/' % context.uuid)
        # context
        self.context = context

    @property
    def consumer(self):
        """
        Access to I{consumer} capability.
        @return: Consumer API.
        @rtype: L{Consumer}
        """
        return Consumer(self.context)

    @property
    def content(self):
        """
        Access to I{content} capability.
        @return: Content API.
        @rtype: L{Content}
        """
        return Content(self.context)

    @property
    def profile(self):
        """
        Access to I{profile} capability.
        @return: Profile API.
        @rtype: L{Profile}
        """
        return Profile(self.context)

    @classmethod
    def status(self, uuids):
        """
        Get the status of the agent.
        Relies on heartbeat.
        @param uuids: A list of uuids.
        @type uuids: list
        @return: {}
        """
        rest = Rest()
        path = '/agenthub/agent/%s/' % uuids[0]
        reply = rest.get(path)
        return reply[1]

#
# Agent Capability(s)
#


class Consumer(Capability):
    """
    The consumer management capability.
    """

    def unregistered(self):
        """
        Notification that the consumer has been unregistered.
        Registration artifacts are cleaned up.
        @return: Tuple (<httpcode>, None); 202 expected.
        @rtype: tuple
        """
        agent = Agent(
            self.context.uuid,
            rest=Rest(),
            secret=self.context.secret,
            async=True)
        consumer = agent.Consumer()
        status, result = consumer.unregistered()
        if status != 202:
            raise Exception('Unregistered Failed')
        return (status, result)

    def bind(self, repo_id):
        """
        Bind a consumer to the specified repository.
        @param repo_id: A repository ID.
        @type repo_id: str
        @return: Tuple (<httpcode>, None); 202 expected.
        @rtype: tuple
        """
        agent = Agent(
            self.context.uuid,
            rest=Rest(),
            secret=self.context.secret,
            async=True)
        consumer = agent.Consumer()
        status, result = consumer.bind(repo_id)
        if status != 202:
            raise Exception('Bind Failed')
        return (status, result)

    def unbind(self, repo_id):
        """
        Unbind a consumer from the specified repository.
        @param repo_id: A repository ID.
        @type repo_id: str
        @return: Tuple (<httpcode>, None); 202 expected.
        @rtype: tuple
        """
        agent = Agent(
            self.context.uuid,
            rest=Rest(),
            secret=self.context.secret,
            async=True)
        consumer = agent.Consumer()
        status, result = consumer.unbind(repo_id)
        if status != 202:
            raise Exception('Unbind Failed')
        return (status, result)


class Content(Capability):
    """
    The content management capability.
    """

    def install(self, units, options):
        """
        Install content on a consumer.
        @param units: A list of content units to be installed.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }
        @param options: Install options; based on unit type.
        @type options: dict
        @return: Tuple (<httpcode>, None); 202 expected.
        @rtype: tuple
        """
        agent = Agent(
            self.context.uuid,
            rest=Rest(),
            timeout=(10, 90),
            secret=self.context.secret,
            replyto=self.context.replyto,
            any=self.context.taskid)
        content = agent.Content()
        status, result = content.install(units, options)
        if status != 202:
            raise Exception('Install Failed')
        return (status, result)

    def update(self, units, options):
        """
        Update content on a consumer.
        @param units: A list of content units to be updated.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }
        @param options: Update options; based on unit type.
        @type options: dict
        @return: Tuple (<httpcode>, None); 202 expected.
        @rtype: tuple
        """
        agent = Agent(
            self.context.uuid,
            rest=Rest(),
            timeout=(10, 90),
            secret=self.context.secret,
            replyto=self.context.replyto,
            any=self.context.taskid)
        content = agent.Content()
        status, result = content.update(units, options)
        if status != 202:
            raise Exception('Update Failed')
        return (status, result)

    def uninstall(self, units, options):
        """
        Uninstall content on a consumer.
        @param units: A list of content units to be uninstalled.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }
        @param options: Uninstall options; based on unit type.
        @type options: dict
        @return: Tuple (<httpcode>, None); 202 expected.
        @rtype: tuple
        """
        agent = Agent(
            self.context.uuid,
            rest=Rest(),
            timeout=(10, 90),
            secret=self.context.secret,
            replyto=self.context.replyto,
            any=self.context.taskid)
        content = agent.Content()
        status, result = content.uninstall(units, options)
        if status != 202:
            raise Exception('Uninstall Failed')
        return (status, result)

class Profile(Capability):
    """
    The profile management capability.
    """

    def send(self):
        """
        Request the agent to send the package profile.
        @return: The RMI request serial number.
        @rtype: str
        @return: Tuple (<httpcode>, None); 202 expected.
        @rtype: tuple
        """
        agent = Agent(
            self.context.uuid,
            rest=Rest(),
            secret=self.context.secret)
        profile = agent.Profile()
        status, result = profile.send()
        if status != 202:
            raise Exception('Profile Failed')
        return (status, result)
