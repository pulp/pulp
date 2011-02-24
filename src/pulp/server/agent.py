#! /usr/bin/env python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

"""
Contains (proxy) classes that represent the pulp agent.
The proxy classes must match the names of classes that are exposed
on the agent.
"""

from gofer.proxy import Agent as Base
from gofer.messaging.producer import Producer
from pulp.server.config import config

def retrieve_agent(uuid, **options):
    '''
    Factory method for getting Agent instances. This method can be monkey patched
    in unit tests to return a mock agent suitable for testing.

    @param uuid: uuid of the consumer
    @type  uuid: string

    @param options: options to the underlying message bus
    @type  options: dict
    '''
    return Agent(uuid, **options)

def retrieve_repo_proxy(uuid, **options):
    '''
    Utility factory method for retrieving the repo proxy to a consumer.

    @param uuid: uuid of the consumer
    @type  uuid: string

    @param options: options to the underlying message bus
    @type  options: dict
    '''
    agent = retrieve_agent(uuid, **options)
    return agent.Repo()

class Agent(Base):
    """
    A server-side proxy for the pulp agent.
    """

    def __init__(self, uuid, **options):
        """
        @param uuid: The consumer uuid.
        @type uuid: str|list
        @param options: Messaging L{gofer.messaging.Options}
        """
        url = config.get('messaging', 'url')
        producer = Producer(url=url)
        Base.__init__(self, uuid, producer, **options)