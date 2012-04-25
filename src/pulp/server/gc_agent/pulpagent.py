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

import hashlib
from pulp.server.gc_agent.rest import Rest
from pulp.server.gc_agent.client import Agent
from pulp.server.dispatch import factory
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
        context = Context()
        context.uuid = consumer['id']
        # secret
        certificate = consumer.get('certificate')
        hash = hashlib.sha256()
        hash.update(certificate.strip())
        context.secret = hash.hexdigest()
        context.taskid = factory.context().task_id
        self.context = context
        
    @property
    def consumer(self):
        return Consumer(self.context)
    
    @property
    def content(self):
        return Content(self.context)
    
    @property
    def profile(self):
        return Profile(self.context)

    def status(self):
        """
        Get the status of the agent.
        Relies on heartbeat.
        @return: {}
        """
        rest = Rest()
        path = '/agenthub/agent/%s/' % self.uuid
        reply = rest.get(path)
        return reply[1]

#
# Agent Capability(s)
#

class Context(dict):
    """
    The capability context.
    """
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class Capability:
    """
    An agent capability.
    @ivar context: The context.
    @type context: L{Context}
    """

    def __init__(self, context):
        """
        @param context: The capability context.
        @type context: L{Context}
        """
        self.context = context


class Consumer(Capability):
    """
    The consumer management capability.
    """

    def unregistered(self):
        """
        Notification that the consumer has been unregistered.
        Registration artifacts are cleaned up.
        """
        agent = Agent(
            self.context.uuid,
            rest=Rest(),
            secret=self.context.secret,
            async=True)
        consumer = agent.Consumer()
        status, result = consumer.unregistered()
        # TODO: process
        return result

    def bind(self, repo_id):
        """
        Bind a consumer to the specified repository.
        @param repo_id: A repository ID.
        @type repo_id: str
        """
        agent = Agent(
            self.context.uuid,
            rest=Rest(),
            secret=self.context.secret,
            async=True)
        consumer = agent.Consumer()
        result = consumer.bind(repo_id)
        # TODO: process
        return result

    def unbind(self, repo_id):
        """
        Unbind a consumer from the specified repository.
        @param repo_id: A repository ID.
        @type repo_id: str
        """
        agent = Agent(
            self.context.uuid,
            rest=Rest(),
            secret=self.context.secret,
            async=True)
        consumer = agent.Consumer()
        result = consumer.unbind(repo_id)
        # TODO: process
        return result


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
        """
        taskid = self.context.get('taskid')
        agent = Agent(
            self.context.uuid,
            rest=Rest(),
            timeout=(10, 90),
            secret=self.context.secret,
            ctag='pulp',
            any=taskid)
        content = agent.Content()
        result = content.install(units, options)
        # TODO: process
        return result

    def update(self, units, options):
        """
        Update content on a consumer.
        @param units: A list of content units to be updated.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }
        @param options: Update options; based on unit type.
        @type options: dict
        """
        taskid = self.context.get('taskid')
        agent = Agent(
            self.context.uuid,
            rest=Rest(),
            timeout=(10, 90),
            secret=self.context.secret,
            ctag='pulp',
            any=taskid)
        content = agent.Content()
        result = content.update(units, options)
        # TODO: process
        return result

    def uninstall(self, units, options):
        """
        Uninstall content on a consumer.
        @param units: A list of content units to be uninstalled.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }
        @param options: Uninstall options; based on unit type.
        @type options: dict
        """
        taskid = self.context.get('taskid')
        agent = Agent(
            self.context.uuid,
            rest=Rest(),
            timeout=(10, 90),
            secret=self.context.secret,
            ctag='pulp',
            any=taskid)
        content = agent.Content()
        result = content.uninstall(units, options)
        # TODO: process
        return result


class Profile(Capability):
    """
    The profile management capability.
    """

    def send(self):
        agent = Agent(
            self.context.uuid,
            rest=Rest(),
            secret=self.context.secret)
        profile = agent.Profile()
        result = profile.send()
        # TODO: process
        return result
