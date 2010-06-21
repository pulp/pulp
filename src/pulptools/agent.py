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

from pmf.base import Agent as Base
from pmf.consumer import Consumer
from pmf.decorators import remote, remotemethod
from pulptools.repolib import RepoLib


@remote
class Repo:

    @remotemethod
    def update(self):
        rlib = RepoLib()
        rlib.update()


@remote
class PackageInstaller:

    @remotemethod
    def installpackages(self, packagenames):
        pass


class Agent(Base):
    """
    Pulp agent.
    """
    def __init__(self):
        id = self.id()
        cfg = Config()
        host = cfg.pmf.host
        port = cfg.pmf.port
        consumer = Consumer(id, host, port)
        Base.__init__(self, consumer)

    def id(self):
        return 'agent:%s' % ConsumerId()