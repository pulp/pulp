#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Jeff Ortel <jortel@redhat.com>
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
Class for pulp agent.
"""

from time import sleep
from pmf.base import Agent as Base
from pmf.consumer import Consumer
from pmf.decorators import remote, remotemethod
from pulptools import ConsumerId
from pulptools.config import Config
from pulptools.repolib import RepoLib
from pulptools.logutil import getLogger
from yum import YumBase

log = getLogger(__name__)


@remote
class Repo:
    """
    Pulp (pulp.repo) yum repository object.
    """

    @remotemethod
    def update(self):
        """
        Update the pulp.repo based on information
        retrieved from pulp server.
        """
        log.info('updating yum repo')
        rlib = RepoLib()
        rlib.update()


@remote
class Packages:
    """
    Package management object.
    """

    @remotemethod
    def install(self, packagenames):
        """
        Install packages by name.
        @param packagenames: A list of simple package names.
        @param packagenames: str
        """
        log.info('installing packages: %s', packagenames)
        yb = YumBase()
        for n in packagenames:
            pkgs = yb.pkgSack.returnNewestByName(n)
            for p in pkgs:
                yb.tsInfo.addInstall(p)
        yb.resolveDeps()
        yb.processTransaction()


@remote
class AgentAdmin:

    @remotemethod
    def hello(self):
        s = []
        cfg = Config()
        cid = ConsumerId()
        s.append('Hello, I am agent "%s"' % cid.uuid)
        s.append('Here is my configuration:\n%s' % cfg)
        s.append('Status: ready')
        return '\n'.join(s)


class Agent(Base):
    """
    Pulp agent.
    """
    def __init__(self):
        id = self.id()
        cfg = Config()
        host = cfg.pmf.host
        port = int(cfg.pmf.port)
        consumer = Consumer(id, host, port)
        log.info('starting ...')
        Base.__init__(self, consumer)

    def id(self):
        cid = ConsumerId()
        while ( not cid.uuid ):
            log.info('Not registered.')
            sleep(10)
            cid.read()
        return cid.uuid


if __name__ == '__main__':
    Agent()
