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
import os
from yum.plugins import TYPE_CORE
from pulp.client.consumer.credentials import Consumer as ConsumerBundle
from pulp.client.api.consumer import ConsumerAPI
from rhsm.profile import get_profile
from pulp.client.api.server import PulpServer, set_active_server
from pulp.client.consumer.config import ConsumerConfig

requires_api_version = '2.5'
plugin_type = (TYPE_CORE,)

def get_consumer():
    """
    Get consumer bundle
    """
    bundle = ConsumerBundle()
    return bundle

def pulpserver():
    """
    Pulp server configuration
    """
    cfg = ConsumerConfig()
    bundle = get_consumer()
    pulp = PulpServer(cfg.server.host, timeout=10)
    pulp.set_ssl_credentials(bundle.crtpath())
    set_active_server(pulp)

def update_consumer_profile(cid):
    """
    Updates consumer package profile information
    @param cid: Consumer ID
    @type cid: str
    """
    pulpserver()
    capi = ConsumerAPI()
    pkginfo = get_profile("rpm").collect()
    capi.package_profile(cid, pkginfo)

def posttrans_hook(conduit):
    """
    Update Package Profile for available consumer.
    """
    #get configuration
    verbose = conduit.confBool("main", "verbose", default=1)
    if os.getuid() != 0:
        if verbose:
            conduit.info(2, 'Not root, Pulp consumer profile not updated')
        return
    if hasattr(conduit, 'registerPackageName'):
        conduit.registerPackageName("pulp-client")
    try:
        bundle = get_consumer()
        cid = bundle.getid()
        if not cid:
            if verbose:
                conduit.info(2, "Consumer Id could not be found. Cannot update consumer profile.")
            return
        update_consumer_profile(cid)
        if verbose:
            conduit.info(2, "Profile updated successfully for consumer [%s]" % cid)
    except Exception, e:
        conduit.error(2, str(e))

