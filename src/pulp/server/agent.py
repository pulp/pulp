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
The proxy classes must match the names of classes that are exposed
on the agent.
"""

import hashlib
from gofer import proxy
from pulp.server.config import config
from logging import getLogger


log = getLogger(__name__)


class Agent:
    """
    Agent (proxy) base class.
    @ivar __agent: The wrapped gofer agent object.
    @type __agent: Agent
    """

    def __init__(self, uuid, **options):
        """
        @param __agent: The wrapped gofer agent object.
        @type __agent: Agent
        """
        options['url'] = \
            config.get('messaging', 'url')
        self.__agent = proxy.agent(uuid, **options)

    def __getattr__(self, name):
        return getattr(self.__agent, name)


class PulpAgent(Agent):
    """
    Represents a pulp agent (proxy).
    """

    @classmethod
    def getsecret(cls, consumer):
        """
        Get the shared secret for the specified consumer.
        Derived from sha256 of credentials which are basically
        just the private key and certificate PEM.
        @param consumer: A consumer model object.
        @type consumer: dict
        """
        secret = None
        certificate = consumer.get('certificate')
        if certificate:
            hash = hashlib.sha256()
            hash.update(certificate.strip())
            secret = hash.hexdigest()
        return secret

    def __init__(self, consumer, **options):
        """
        @param consumer: A consumer model object.
        @type consumer: dict
        @keyword async: The asynchronous RMI flag.
        @keyword timeout: The request timeout (seconds).
        """
        uuid = consumer['id']
        options['secret'] = self.getsecret(consumer)
        Agent.__init__(self, uuid, **options)


class CdsAgent(Agent):
    """
    Represents a CDS agent (proxy).
    """

    @classmethod
    def uuid(cls, cds):
        return 'cds-%s' % cds['hostname']

    def __init__(self, cds, **options):
        """
        @param cds: A cds model object.
        @type cds: dict
        @keyword async: The asynchronous RMI flag.
        @keyword timeout: The request timeout (seconds).
        """
        uuid = self.uuid(cds)
        options['secret'] = cds.get('secret')
        Agent.__init__(self, uuid, **options)
