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
Pulp (gofer) plugin.
Contains recurring actions and remote classes.
"""

import os
from pulp.client.connection import ConsumerConnection, RestlibException
from pulp.client.package_profile import PackageProfile
from pulp.client.config import Config
from pulp.client.repolib import RepoLib
from pulp.client.credentials import Consumer
from gofer.agent.action import *
from gofer.decorators import *
from yum import YumBase

from logging import getLogger

log = getLogger(__name__)
cfg = Config()


@remote
@action(minutes=cfg.server.interval)
class ProfileUpdateAction(Action):
    """
    Package Profile Update Action to update installed package info for a
    registered consumer
    """
    @remotemethod
    def perform(self):
        """
        Looks up the consumer id and latest pkg profile info and cals
        the api to update the consumer profile
        """
        bundle = Consumer()
        cid = bundle.getid()
        if not cid.exists():
            log.error("Not Registered")
            return
        try:
            cconn = ConsumerConnection(host=cfg.server.host or "localhost",
                                       port=cfg.server.port or 443)
            pkginfo = PackageProfile().getPackageList()
            cconn.profile(cid.read(), pkginfo)
            log.info("Profile updated successfully for consumer %s" % cid.read())
        except RestlibException, re:
            log.error("Error: %s" % re)
        except Exception, e:
            log.error("Error: %s" % e)


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
        return packagegroupids


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


@identity
class PulpIdentity:

    def getuuid(self):
        bundle = Consumer()
        return bundle.getid()
