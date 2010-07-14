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
from pmf.producer import QueueProducer
from pmf.policy import *
from pulp.util import Config


class AgentAdmin(Proxy):
    pass

class Repo(Proxy):
    pass

class Packages(Proxy):
    pass

class PackageGroups(Proxy):
    pass

class Shell(Proxy):
    pass

class Agent(Base):
    """
    A proxy for the agent.
    """
    def __init__(self, uuid, tag=None):
        """
        @param uuid: The consumer uuid.
        @type uuid: str|list
        @param tag: An (optional) asynchronous correlation tag.
        @type tag: str
        """
        cfg = Config()
        host = cfg.pmf.host
        port = int(cfg.pmf.port)
        producer = QueueProducer(host=host, port=port)
        if tag or isinstance(uuid, (tuple,list)):
            method = Asynchronous(producer, tag)
        else:
            method = Synchronous(producer)
        Base.__init__(self,
            uuid,
            method,
            admin=AgentAdmin,
            repo=Repo,
            packages=Packages,
            packagegroups=PackageGroups,
            shell=Shell,)
