#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

"""
Pulp (gofer) plugin.
Contains recurring actions and remote classes.
"""

import os
from hashlib import sha256
from pulp.client.lib import repolib
from pulp.client.api.server import PulpServer, set_active_server
from pulp.client.api.consumer import ConsumerAPI
from rhsm.profile import get_profile
from pulp.client.consumer.config import *
from pulp.client.lib.repo_file import RepoFile
from pulp.client.consumer.credentials import Consumer as ConsumerBundle
from gofer.agent.plugin import Plugin
from gofer.messaging import Topic
from gofer.messaging.producer import Producer
from gofer.pmon import PathMonitor
from gofer.decorators import *

from logging import getLogger

log = getLogger(__name__)
plugin = Plugin.find(__name__)
cfg = ConsumerConfig()

HEARTBEAT = cfg.heartbeat.seconds

# plugin exports
package = Plugin.find('package')
Package = package.export('Package')
PackageGroup = package.export('PackageGroup')


def pulpserver():
    """
    Pulp server configuration
    """
    bundle = ConsumerBundle()
    pulp = PulpServer(cfg.server.host)
    pulp.set_ssl_credentials(bundle.crtpath())
    set_active_server(pulp)

def getsecret():
    """
    Get the shared secret used for auth of RMI requests.
    @return: The sha256 for the certificate & key
    @rtype: str
    """
    bundle = ConsumerBundle()
    content = bundle.read()
    if content:
        hash = sha256()
        hash.update(content)
        return hash.hexdigest()
    else:
        return None

#
# Actions
#

class Heartbeat:
    """
    Provide agent heartbeat.
    """

    __producer = None

    @classmethod
    def producer(cls):
        if not cls.__producer:
            broker = plugin.getbroker()
            url = str(broker.url)
            cls.__producer = Producer(url=url)
        return cls.__producer

    @action(seconds=HEARTBEAT)
    def heartbeat(self):
        return self.send()

    @remote
    def send(self):
        topic = Topic('heartbeat')
        delay = int(HEARTBEAT)
        bundle = ConsumerBundle()
        myid = bundle.getid()
        if myid:
            p = self.producer()
            body = dict(uuid=myid, next=delay)
            p.send(topic, ttl=delay, heartbeat=body)
        return myid


class RegistrationMonitor:
    
    pmon = PathMonitor()
    
    @classmethod
    @action(days=0x8E94)
    def init(cls):
        """
        Start path monitor to track changes in the
        pulp identity certificate.
        """
        bundle = ConsumerBundle()
        path = bundle.crtpath()
        cls.pmon.add(path, cls.changed)
        cls.pmon.start()

    @classmethod
    def changed(cls, path):
        """
        A change in the pulp certificate has been detected.
        When deleted: disconnect from qpid.
        When added/updated: reconnect to qpid.
        @param path: The changed file (ignored).
        @type path: str
        """
        log.info('changed: %s', path)
        bundle = ConsumerBundle()
        plugin.setuuid(bundle.getid())


class ProfileUpdateAction:
    """
    Package Profile Update Action to update installed package info for a
    registered consumer
    """
    @remote(secret=getsecret)
    @action(minutes=cfg.server.interval)
    def perform(self):
        """
        Looks up the consumer id and latest pkg profile info and cals
        the api to update the consumer profile
        """
        bundle = ConsumerBundle()
        cid = bundle.getid()
        if not cid:
            log.error("Not Registered; cannot update consumer profile.")
            return
        try:
            pulpserver()
            capi = ConsumerAPI()
            pkginfo = get_profile("rpm").collect()
            capi.package_profile(cid, pkginfo)
            log.info("Profile updated successfully for consumer [%s]" % cid)
        except Exception, e:
            log.error("Error: %s" % e)

#
# API
#
            
class Packages:
    """
    Package management object.
    """

    @remote(secret=getsecret)
    def install(self, names, reboot=False, assumeyes=False):
        """
        Install packages by name.
        @param names: A list of package names.
        @type names: [str,]
        @param reboot: Request reboot after packages are installed.
        @type reboot: bool
        @param assumeyes: Assume (yes) to yum prompts.
        @type assumeyes: bool
        @return: (installed, (reboot requested, performed))
        @rtype: tuple
        """
        pkg = Package()
        installed = pkg.install(names, assumeyes)
        scheduled = False
        if reboot:
            approved = getbool(cfg.client, assumeyes=assumeyes)
            if approved:
                self.__schedule_reboot()
                scheduled = True
        return (installed, (reboot, scheduled))

    @remote(secret=getsecret)
    def uninstall(self, names):
        """
        Uninstall (erase) packages by name.
        @param names: A list of package names to be removed.
        @type names: list
        @return: A list of erased packages.
        @rtype: list
        """
        pkg = Package()
        uninstalled = pkg.uninstall(names)
        log.info('Packages uninstalled: %s', uninstalled)
        return uninstalled

    def __schedule_reboot(self):
        interval = cfg.client.reboot_schedule
        os.system("shutdown -r %s &", interval)
        log.info("System is scheduled to reboot in %s minutes", interval)


class PackageGroups:
    """
    PackageGroup management object
    """

    @remote(secret=getsecret)
    def install(self, names):
        """
        Install package groups by name.
        @param names: A list of package names.
        @param names: str
        """
        grp = PackageGroup()
        installed = grp.install(names)
        log.info('Packages installed: %s', installed)
        return installed

    @remote(secret=getsecret)
    def uninstall(self, names):
        """
        Uninstall package groups by name.
        @param names: A list of package group names.
        @param names: str
        """
        grp = PackageGroup()
        uninstalled = grp.uninstall(names)
        log.info('Packages uninstalled: %s', uninstalled)
        return uninstalled
