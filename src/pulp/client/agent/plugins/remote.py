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

import os
from pulp.client import *
from pulp.client.repolib import RepoLib
from pulp.client.config import Config
from pulp.messaging.decorators import *
from yum import YumBase
from logging import getLogger

log = getLogger(__name__)


@remote
@alias(name=['RepoLib', 'repolib'])
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
@alias(name='packages')
class Packages:
    """
    Package management object.
    """

    @remotemethod
    def install(self, packageinfo):
        """
        Install packages by name.
        @param packageinfo: A list of strings for pkg names
                            or tuples for name/arch info.
        @type packageinfo: str or tuple
        """
        installed = []
        yb = YumBase()
        log.info('installing packages: %s', packageinfo)
        for info in packageinfo:
            if isinstance(info, list):
                pkgs = yb.pkgSack.returnNewestByNameArch(tuple(info))
            else:
                pkgs = yb.pkgSack.returnNewestByName(info)
            for p in pkgs:
                installed.append(str(p))
                yb.tsInfo.addInstall(p)
        yb.resolveDeps()
        yb.processTransaction()
        return installed

@remote
@alias(name='packagegroups')
class PackageGroups:
    """
    PackageGroup management object
    """

    @remotemethod
    def install(self, packagegroupids):
        """
        Install packagegroups by id.
        @param packagegroupids: A list of package ids.
        @param packagegroupids: str
        """
        log.info('installing packagegroups: %s', packagegroupids)
        yb = YumBase()
        for grp_id in packagegroupids:
            txmbrs = yb.selectGroup(grp_id)
            log.info("Added '%s' group to transaction, packages: %s", grp_id, txmbrs)
        yb.resolveDeps()
        yb.processTransaction()

@remote
@alias(name='admin')
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


@remote
@alias(name='shell')
class Shell:

    @remotemethod
    def run(self, cmd):
        """
        Run a shell command.
        @param cmd: The command & arguments.
        @type cmd: str
        @return: The command output.
        @rtype: str
        """
        f = os.popen(cmd)
        try:
            return f.read()
        finally:
            f.close()
