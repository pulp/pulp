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
Remoted class for pulp agent.
"""

from pulptools import *
from pulptools.repolib import RepoLib
from pulptools.config import Config
from pmf.decorators import remote, remotemethod
from yum import YumBase
from logging import getLogger

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
class PackageGroups:
    """
    PackageGroup management object
    """
    
    @remotemethod
    def install(self, packagegroupids):
        """
        Install packagegroups by id.
        @param packageids: A list of package ids.
        @param packageids: str
        """
        log.info('installing packagegroups: %s', packagegroupids)
        yb = YumBase()
        for grp_id in packagegroupids:
            log.info("Need to add yum API calls to do package group install for: %s" % (grp_id))
            #pkgs = yb.pkgSack.returnNewestByName(n)
            #for p in pkgs:
            #    yb.tsInfo.addInstall(p)
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
