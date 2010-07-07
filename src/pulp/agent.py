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

from pmf.proxy import Proxy
from pmf.base import AgentProxy as Base
from pmf.producer import RequestProducer
from pulp.util import Config


class AgentAdmin(Proxy):
    pass

class Repo(Proxy):
    pass

class Packages(Proxy):
    pass


class Agent(Base):
    """
    A proxy for the agent.
    """
    def __init__(self, uuid):
        """
        @param uuid: The consumer uuid.
        @type uuid: str
        """
        cfg = Config()
        host = cfg.pmf.host
        port = int(cfg.pmf.port)
        producer = RequestProducer(host=host, port=port)
        self.admin = AgentAdmin(uuid, producer)
        self.repo = Repo(uuid, producer)
        self.packages = Packages(uuid, producer)
        Base.__init__(self, producer)
