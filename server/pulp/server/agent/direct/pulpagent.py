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
The purpose of the proxy is the insulate pulp from the implementation
of making agent requests.  The context bundles together all of the information
needed to invoke the remote method on the agent and where the asynchronous reply
is to be sent.  Further, gofer supports including arbitrary information to be
round tripped.  This is contextual information that the asynchronous reply handler
will need to process the reply.  We include such things as: The task_id and in
some cases DB entity IDs so we can update the DB based on the result of the
operation on the agent.

Agent request flow:
- Invoke the RMI
- Work performed on the consumer.
- The agent sends the RMI result to the reply queue.
- The pulp reply consumer updates the DB as needed.
"""

from logging import getLogger

from gofer.proxy import Agent


log = getLogger(__name__)


# --- Agent ------------------------------------------------------------------

class PulpAgent(object):
    """
    Represents a remote pulp agent.
    """

    @property
    def consumer(self):
        """
        Access to *consumer* capability.
        :return: Consumer API.
        :rtype: Consumer
        """
        return Consumer

    @property
    def content(self):
        """
        Access to *content* capability.
        :return: Content API.
        :rtype: Content
        """
        return Content

    @property
    def profile(self):
        """
        Access to *profile* capability.
        :return: Profile API.
        :rtype: Profile
        """
        return Profile

    @staticmethod
    def cancel(context, task_id):
        """
        Cancel an agent request by task ID.
        :param task_id: The ID of a task associated with an agent request.
        :type task_id: str
        """
        criteria = {'match': {'task_id': task_id}}
        agent = Agent(
            context.agent_id,
            url=context.url,
            authenticator=context.authenticator,
            transport=context.transport,
            async=True)
        admin = agent.Admin()
        admin.cancel(criteria=criteria)


# --- Agent Capabilities -----------------------------------------------------


class Consumer(object):
    """
    The consumer management capability.
    """

    @staticmethod
    def unregistered(context):
        """
        Notification that the consumer has been unregistered.
        Registration artifacts are cleaned up.
        :param context: The call context.
        :type context: pulp.server.agent.context.Context
        """
        agent = Agent(
            context.agent_id,
            url=context.url,
            secret=context.secret,
            authenticator=context.authenticator,
            transport=context.transport,
            async=True)
        consumer = agent.Consumer()
        consumer.unregistered()

    @staticmethod
    def bind(context, bindings, options):
        """
        Bind a consumer to the specified repository.
        :param context: The call context.
        :type context: pulp.server.agent.context.Context
        :param bindings: A list of bindings to add/update.
          Each binding is: {type_id:<str>, repo_id:<str>, details:<dict>}
            The 'details' are at the discretion of the distributor.
        :type bindings: list
        :param options: Bind options.
        :type options: dict
        """
        agent = Agent(
            context.agent_id,
            url=context.url,
            secret=context.secret,
            authenticator=context.authenticator,
            transport=context.transport,
            ctag=context.reply_queue,
            any=context.details)
        consumer = agent.Consumer()
        consumer.bind(bindings, options)

    @staticmethod
    def unbind(context, bindings, options):
        """
        Unbind a consumer from the specified repository.
        :param context: The call context.
        :type context: pulp.server.agent.context.Context
        :param bindings: A list of bindings to be removed.
          Each binding is: {type_id:<str>, repo_id:<str>}
        :type bindings: list
        :param options: Unbind options.
        :type options: dict
        """
        agent = Agent(
            context.agent_id,
            url=context.url,
            secret=context.secret,
            authenticator=context.authenticator,
            transport=context.transport,
            ctag=context.reply_queue,
            any=context.details)
        consumer = agent.Consumer()
        consumer.unbind(bindings, options)


class Content(object):
    """
    The content management capability.
    """

    @staticmethod
    def install(context, units, options):
        """
        Install content on a consumer.
        :param context: The call context.
        :type context: pulp.server.agent.context.Context
        :param units: A list of content units to be installed.
        :type units: list of:
            { type_id:<str>, unit_key:<dict> }
        :param options: Install options; based on unit type.
        :type options: dict
        """
        agent = Agent(
            context.agent_id,
            url=context.url,
            secret=context.secret,
            authenticator=context.authenticator,
            transport=context.transport,
            ctag=context.reply_queue,
            any=context.details)
        content = agent.Content()
        content.install(units, options)

    @staticmethod
    def update(context, units, options):
        """
        Update content on a consumer.
        :param context: The call context.
        :type context: pulp.server.agent.context.Context
        :param units: A list of content units to be updated.
        :type units: list of:
            { type_id:<str>, unit_key:<dict> }
        :param options: Update options; based on unit type.
        :type options: dict
        """
        agent = Agent(
            context.agent_id,
            url=context.url,
            secret=context.secret,
            authenticator=context.authenticator,
            transport=context.transport,
            ctag=context.reply_queue,
            any=context.details)
        content = agent.Content()
        content.update(units, options)

    @staticmethod
    def uninstall(context, units, options):
        """
        Uninstall content on a consumer.
        :param context: The call context.
        :type context: pulp.server.agent.context.Context
        :param units: A list of content units to be uninstalled.
        :type units: list of:
            { type_id:<str>, unit_key:<dict> }
        :param options: Uninstall options; based on unit type.
        :type options: dict
        """
        agent = Agent(
            context.agent_id,
            url=context.url,
            secret=context.secret,
            authenticator=context.authenticator,
            transport=context.transport,
            ctag=context.reply_queue,
            any=context.details)
        content = agent.Content()
        content.uninstall(units, options)


class Profile(object):
    """
    The profile management capability.
    """

    @staticmethod
    def send(context):
        """
        Request the agent to send the package profile.
        :param context: The call context.
        :type context: pulp.server.agent.context.Context
        """
        agent = Agent(
            context.agent_id,
            url=context.url,
            secret=context.secret,
            authenticator=context.authenticator,
            transport=context.transport)
        profile = agent.Profile()
        profile.send()
