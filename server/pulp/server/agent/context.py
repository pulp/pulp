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

import hashlib

from pulp.server.dispatch import factory
from pulp.server.config import config


class Capability:
    """
    Agent capabilities provide both namespacing and central
    access to call context.
    @ivar context: The context.
    @type context: L{Context}
    """

    def __init__(self, context):
        """
        @param context: The capability context.
        @type context: L{Context}
        """
        self.context = context


class Context(object):
    """
    The remote method invocation context provides call
    context sensitive options and settings.
    @ivar uuid: The agent UUID.
    @type uiud: str
    @ivar url: The broker URL.
    @type url: str
    @ivar secret: The server agent shared secret for the consumer.
    @type secret: str
    @ivar call_request_id: The ID of the call request when
        the call is being executed by the dispatch system.
        This ID is round-tripped to the agent and used by the
        reply listener for task lookup.
    """

    def __init__(self, consumer):
        self.uuid = consumer['id']
        self.url = config.get('messaging', 'url')
        certificate = consumer.get('certificate')
        hash = hashlib.sha256()
        hash.update(certificate.strip())
        self.secret = hash.hexdigest()
        self.call_request_id = factory.context().call_request_id

    def get_timeout(self, option):
        """
        Get a timeout option from the server configuration.
        The value is parsed and converted into a gofer
        timeout tuple.
        @param option: The name of a config option.
        @type option: str
        @return: A gofer timeout tuple: (<initial>, <duration>).
        @rtype tuple
        """
        value = config.get('messaging', option)
        initial, duration = value.split(':')
        return initial, duration
