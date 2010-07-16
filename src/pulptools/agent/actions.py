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
Action classes for pulp agent.
** Add custome actions here **
"""

from pulptools import ConsumerId
from pulptools.agent.action import *
from pulptools.connection import ConsumerConnection, RestlibException
from pulptools.package_profile import PackageProfile
from pulptools.config import Config
from logging import getLogger

log = getLogger(__name__)
cfg = Config()


@action(minutes=10)
class TestAction(Action):
    
    def perform(self):
        log.info('Hello')


@action(minutes=cfg.server.interval)
class ProfileUpdateAction(Action):
    """
    Package Profile Update Action to update installed package info for a 
    registered consumer
    """

    def perform(self):
        """ 
        Looks up the consumer id and latest pkg profile info and cals
        the api to update the consumer profile 
        """
        cid = ConsumerId()
        if not cid.exists():
            log.error("Not Registered")
            return
        try:
            cconn = ConsumerConnection(host=cfg.server.host or "localhost", 
                                       port=cfg.server.port or 8811)
            pkginfo = PackageProfile().getPackageList()
            cconn.profile(cid.read(), pkginfo)
            log.info("Profile updated successfully for consumer %s" % cid.read())
        except RestlibException, re:
            log.error("Error: %s" % re)
        except Exception, e:
            log.error("Error: %s" % e)

