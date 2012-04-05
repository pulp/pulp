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
from agenthub.rest import Rest as RestImpl
from agenthub.client import Agent
from pulp.server.exceptions import PulpDataException
from logging import getLogger


log = getLogger(__name__)

#
# HTTP/REST transport factory
#
def Rest():
    return RestImpl()

#
# Agent
#

class PulpAgent:
    """
    Represents a remote pulp agent.
    """

    def __init__(self, consumer, taskid=None):
        context = Context()
        context.uuid = consumer['id']
        # secret
        certificate = consumer.get('certificate')
        hash = hashlib.sha256()
        hash.update(certificate.strip())
        context.secret = hash.hexdigest()
        # replyto
        context.replyto = dict(
            systemid='pulp',
            method='POST',
            path='/v2/agent/%s/reply/' % context.uuid)
        context.rest = Rest()
        context.taskid = taskid
        # domain(s)
        self.consumer = Consumer(context)
        self.content = Content(context)
        self.profile = Profile(context)

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
# Agent Domain(s)
#

class Context(dict):
    """
    The domain context.
    """
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class Domain:
    """
    An agent API domain.
    @ivar context: The content context.
    @type context: L{Environment}
    """

    def __init__(self, context):
        """
        @param context: The domain context.
        @type context: L{Context}
        """
        self.context = context


class Consumer(Domain):
    """
    The consumer management API domain.
    """

    def agent(self):
        """
        Get a configured agent proxy.
        @return: A configured proxy.
        @rtype: L{Agent}
        """
        agent = Agent(
            self.context.uuid,
            self.context.rest,
            secret=self.context.secret)
        return agent

    def unregistered(self):
        """
        Notification that the consumer has been unregistered.
        Registration artifacts are cleaned up.
        """
        agent = self.agent()
        consumer = agent.Consumer()
        result = consumer.unregistered()
        # TODO: process
        return result

    def bind(self, repo_id):
        """
        Bind a consumer to the specified repository.
        @param repo_id: A repository ID.
        @type repo_id: str
        """
        agent = self.agent()
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
        agent = self.agent()
        consumer = agent.Consumer()
        result = consumer.unbind(repo_id)
        # TODO: process
        return result


class Content(Domain):
    """
    The content management API domain.
    """

    def agent(self):
        """
        Get a configured agent proxy.
        @return: A configured proxy.
        @rtype: L{Agent}
        """
        taskid = self.context.get('taskid')
        if not taskid:
            raise PulpDataException('taskid required')
        agent = Agent(
            self.context.uuid,
            self.context.rest,
            timeout=(10, 90),
            secret=self.context.secret,
            replyto=self.context.replyto,
            any=taskid)
        return agent

    def install(self, units, options):
        """
        Install content on a consumer.
        @param units: A list of content units to be installed.
        @type units: list of:
            { type_id:<str>, metadata:<dict> }
        @param options: Install options; based on unit type.
        @type options: dict
        """
        agent = self.agent()
        content = agent.Content()
        result = content.install(units, options)
        # TODO: process
        return result

    def update(self, units, options):
        """
        Update content on a consumer.
        @param units: A list of content units to be updated.
        @type units: list of:
            { type_id:<str>, metadata:<dict> }
        @param options: Update options; based on unit type.
        @type options: dict
        """
        agent = self.agent()
        content = agent.Content()
        result = content.update(units, options)
        # TODO: process
        return result

    def uninstall(self, units, options):
        """
        Uninstall content on a consumer.
        @param units: A list of content units to be uninstalled.
        @type units: list of:
            { type_id:<str>, metadata:<dict> }
        @param options: Uninstall options; based on unit type.
        @type options: dict
        """
        agent = self.agent()
        content = agent.Content()
        result = content.uninstall(units, options)
        # TODO: process
        return result


class Profile(Domain):
    """
    The profile management API domain.
    """

    def agent(self):
        """
        Get a configured agent proxy.
        @return: A configured proxy.
        @rtype: L{Agent}
        """
        rest = Rest()
        agent = Agent(
            self.context.uuid,
            self.context.rest,
            secret=self.context.secret)
        return agent

    def send(self):
        agent = self.agent()
        profile = agent.Profile()
        result = profile.send()
        # TODO: process
        return result
