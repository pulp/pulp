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

from pulp.server.config import config as pulp_conf

from pulp.server.agent.auth import Authenticator
from pulp.server.agent.direct.services import Services


class Context(object):
    """
    The context bundles together all of the information needed to invoke the
    remote method on the agent and where the asynchronous reply is to be sent.
    Further, gofer supports including arbitrary information to be round tripped.
    This is contextual information that the asynchronous reply handler will need
    to process the reply.  The context also determines the agent UUID based on the
    consumer ID.  It also generates the shared secret based on the SHA256 hex
    digest of the consumer certificate. We include such things as: The task_id and in
    some cases DB entity IDs so we can update the DB based on the result of the
    operation on the agent.

    :ivar agent_id: The agent ID.
        The agent id has the form: 'pulp.agent.<consumer_id>'.
    :type agent_id: str
    :ivar secret: The shared secret which is the DB consumer object's _id.
    :type secret: str
    :ivar url: The broker URL.
    :type url: str
    :ivar transport: The name of the gofer transport to be used.
    :type transport: str
    :ivar details: Data round tripped to that agent and back.
        Used by the reply consumer.
    :type details: dict
    :ivar reply_queue: The reply queue name.
    :type reply_queue: str
    """

    def __init__(self, consumer, **details):
        """
        :param consumer: A consumer DB model object.
        :type consumer: dict
        :param details: A dictionary of information to be round-tripped.
            Primarily used to correlate asynchronous replies.
        :type details: dict
        """
        self.agent_id = 'pulp.agent.%s' % consumer['id']
        self.secret = str(consumer['_id'])
        self.url = pulp_conf.get('messaging', 'url')
        self.transport = pulp_conf.get('messaging', 'transport')
        self.details = details
        self.reply_queue = Services.REPLY_QUEUE
        self.authenticator = Authenticator()
        self.authenticator.load()
