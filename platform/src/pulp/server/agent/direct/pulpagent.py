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

from logging import getLogger

from gofer.proxy import Agent

from pulp.server.agent.context import Context, Capability
from pulp.server.agent.direct.services import Services



log = getLogger(__name__)


#
# Agent
#

class PulpAgent(object):
    """
    Represents a remote pulp agent.
    """

    def __init__(self, consumer):
        context = Context(consumer)
        context.watchdog = Services.watchdog
        context.ctag = Services.CTAG
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
    def status(cls, uuids):
        """
        Get the status of the agent.
        Relies on heartbeat.
        @param uuids: A list of uuids.
        @type uuids: list
        @return: {}
        """
        return Services.heartbeat_listener.status(uuids)

    def cancel(self, task_id):
        """
        Cancel an agent request by task ID.
        :param task_id: The ID of a task associated with an agent request.
        :type task_id: str
        """
        agent = Agent(
            self.context.uuid,
            url=self.context.url,
            secret=self.context.secret,
            async=True)
        admin = agent.Admin()
        admin.cancel(criteria={'eq': task_id})

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
        @return: The RMI request serial number.
        @rtype: str
        """
        agent = Agent(
            self.context.uuid,
            url=self.context.url,
            secret=self.context.secret,
            async=True)
        consumer = agent.Consumer()
        return consumer.unregistered()

    def bind(self, bindings, options):
        """
        Bind a consumer to the specified repository.
        @param bindings: A list of bindings to add/update.
          Each binding is: {type_id:<str>, repo_id:<str>, details:<dict>}
            The 'details' are at the discretion of the distributor.
        @type bindings: list
        @param options: Bind options.
        @type options: dict
        @return: The RMI request serial number.
        @rtype: str
        """
        agent = Agent(
            self.context.uuid,
            url=self.context.url,
            timeout=self.context.get_timeout('bind_timeout'),
            secret=self.context.secret,
            ctag=self.context.ctag,
            watchdog=self.context.watchdog,
            any=self.context.call_request_id)
        consumer = agent.Consumer()
        return consumer.bind(bindings, options)

    def unbind(self, bindings, options):
        """
        Unbind a consumer from the specified repository.
        @param bindings: A list of bindings to be removed.
          Each binding is: {type_id:<str>, repo_id:<str>}
        @type bindings: list
        @param options: Unbind options.
        @type options: dict
        @return: The RMI request serial number.
        @rtype: str
        """
        agent = Agent(
            self.context.uuid,
            url=self.context.url,
            timeout=self.context.get_timeout('unbind_timeout'),
            secret=self.context.secret,
            ctag=self.context.ctag,
            watchdog=self.context.watchdog,
            any=self.context.call_request_id)
        consumer = agent.Consumer()
        return consumer.unbind(bindings, options)


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
        @return: The RMI request serial number.
        @rtype: str
        """
        agent = Agent(
            self.context.uuid,
            url=self.context.url,
            timeout=self.context.get_timeout('install_timeout'),
            secret=self.context.secret,
            ctag=self.context.ctag,
            watchdog=self.context.watchdog,
            any=self.context.call_request_id)
        content = agent.Content()
        return content.install(units, options)

    def update(self, units, options):
        """
        Update content on a consumer.
        @param units: A list of content units to be updated.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }
        @param options: Update options; based on unit type.
        @type options: dict
        @return: The RMI request serial number.
        @rtype: str
        """
        agent = Agent(
            self.context.uuid,
            url=self.context.url,
            timeout=self.context.get_timeout('update_timeout'),
            secret=self.context.secret,
            ctag=self.context.ctag,
            watchdog=self.context.watchdog,
            any=self.context.call_request_id)
        content = agent.Content()
        return content.update(units, options)

    def uninstall(self, units, options):
        """
        Uninstall content on a consumer.
        @param units: A list of content units to be uninstalled.
        @type units: list of:
            { type_id:<str>, unit_key:<dict> }
        @param options: Uninstall options; based on unit type.
        @type options: dict
        @return: The RMI request serial number.
        @rtype: str
        """
        agent = Agent(
            self.context.uuid,
            url=self.context.url,
            timeout=self.context.get_timeout('uninstall_timeout'),
            secret=self.context.secret,
            ctag=self.context.ctag,
            watchdog=self.context.watchdog,
            any=self.context.call_request_id)
        content = agent.Content()
        return content.uninstall(units, options)


class Profile(Capability):
    """
    The profile management capability.
    """

    def send(self):
        """
        Request the agent to send the package profile.
        @return: The RMI request serial number.
        @rtype: str
        """
        agent = Agent(
            self.context.uuid,
            secret=self.context.secret)
        profile = agent.Profile()
        return profile.send()
