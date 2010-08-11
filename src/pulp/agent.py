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

from pmf.broker import Broker
from pmf.stub import Stub
from pmf.decorators import stub
from pmf.base import Container
from pmf.producer import Producer
from pulp.config import config


@stub('admin')
class AgentAdmin(Stub):
    pass

@stub('repo')
class Repo(Stub):
    pass

@stub('packages')
class Packages(Stub):
    pass

@stub('packagegroups')
class PackageGroups(Stub):
    pass

@stub('shell')
class Shell(Stub):
    pass


class Agent(Container):
    """
    A collection of stubs that represent the agent.
    """

    def __init__(self, uuid, **options):
        """
        @param uuid: The consumer uuid.
        @type uuid: str|list
        @param options: Messaging L{pmf.Options}
        """
        url = config.get('pmf', 'url')
        broker = Broker.get(url)
        broker.cacert = config.get('pmf', 'cacert')
        broker.clientcert = config.get('pmf', 'clientcert')
        producer = Producer(url=url)
        Container.__init__(self, uuid, producer, **options)
