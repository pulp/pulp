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
from pulp.client.credentials import Consumer as ConsumerBundle
from gofer.agent.plugin import Plugin
from gofer.decorators import *
from yum import YumBase

from logging import getLogger

log = getLogger(__name__)
plugin = Plugin.find(__name__)
cfg = Config()


class IdentityAction:
    """
    Detect changes in (pulp) registration status.
    """
    
    last = (0,0)
    
    @action(seconds=1)
    def perform(self):
        """
        Update the plugin's UUID.
        """
        bundle = ConsumerBundle()
        keymod = self.mtime(bundle.keypath())
        crtmod = self.mtime(bundle.crtpath())
        current = (keymod, crtmod)
        if current != self.last:
            plugin.setuuid(bundle.getid())
            self.last = current
    
    def mtime(self, path):
        """
        Get the modification time for the file at path.
        @param path: A file path
        @type path: str
        @return: The mtime or 0.
        """
        try:
            return os.path.getmtime(path)
        except OSError:
            return 0


class ProfileUpdateAction:
    """
    Package Profile Update Action to update installed package info for a
    registered consumer
    """
    @remote
    @action(minutes=cfg.server.interval)
    def perform(self):
        """
        Looks up the consumer id and latest pkg profile info and cals
        the api to update the consumer profile
        """
        bundle = ConsumerBundle()
        cid = bundle.getid()
        if not cid:
            log.error("Not Registered")
            return
        try:
            cconn = ConsumerConnection(host=cfg.server.host or "localhost",
                                       port=cfg.server.port or 443)
            pkginfo = PackageProfile().getPackageList()
            cconn.profile(cid, pkginfo)
            log.info("Profile updated successfully for consumer %s" % cid)
        except RestlibException, re:
            log.error("Error: %s" % re)
        except Exception, e:
            log.error("Error: %s" % e)
            
            
class Consumer:
    """
    Pulp Consumer.
    """
    
    @remote
    def deleted(self, credentials):
        """
        Notification that the consumer has been deleted.
        Clean up associated artifacts.
        @param credentials: The associated x.509 credentials.
        @type credentials: tuple (key,crt)
        """
        bundle = ConsumerBundle()
        found = bundle.read()
        expected = tuple(credentials)
        if found != expected:
            return
        bundle.delete()
        repo = Repo()
        repo.delete()
        log.info('Artifacts deleted')


class Repo:
    """
    Pulp (pulp.repo) yum repository object.
    """

    @remote
    def update(self):
        """
        Update the pulp.repo based on information
        retrieved from pulp server.
        """
        log.info('updating yum repo')
        rlib = RepoLib()
        rlib.update()

    @remote
    def delete(self):
        """
        Delete the .repo file.
        """
        rlib = RepoLib()
        rlib.delete()


class Packages:
    """
    Package management object.
    """

    @remote
    def install(self, packageinfo, reboot_suggested=False, assumeyes=False):
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
        
        if reboot_suggested:
            cfg_assumeyes = cfg.client.assumeyes
            if cfg_assumeyes in ["True", "False"]:
                assumeyes = eval(cfg_assumeyes)
            else:
                assumeyes = assumeyes
            if assumeyes is True:
                self.__schedule_reboot()
                return (installed, {'reboot_performed' :True})
            else:
                return (installed, {'reboot_performed' :False})
                
        return (installed, None)
    
    def __schedule_reboot(self):
        interval = cfg.client.reboot_schedule
        os.system("shutdown -r %s &" % interval)
        log.info("System is scheduled to reboot in %s minutes" % interval)

class PackageGroups:
    """
    PackageGroup management object
    """

    @remote
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


class Shell:

    @remote
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
