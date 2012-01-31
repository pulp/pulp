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

from hashlib import sha256

from gofer.agent.plugin import Plugin

from pulp.client.consumer.credentials import Consumer as ConsumerBundle
from pulp.client.api.server import PulpServer, set_active_server
from pulp.client.consumer.config import ConsumerConfig


def getsecret():
    """
    Get the shared secret used for auth of RMI requests.
    @return: The sha256 for the certificate
    @rtype: str
    """
    bundle = ConsumerBundle()
    content = bundle.read()
    crt = bundle.split(content)[1]
    if content:
        hash = sha256()
        hash.update(crt)
        return hash.hexdigest()
    else:
        return None


class PulpGoferPlugin(object):

    _pulp_plugin = None

    def __init__(self):
        self.cfg = ConsumerConfig()
        self._bundle = None
        self._plugin = None
        self.pulp_plugin = self._pulp_plugin(self.cfg)

    @property
    def bundle(self):
        if not self._bundle:
            self._bundle = ConsumerBundle()
        return self._bundle

    @property
    def plugin(self):
        if not self._plugin:
            self._plugin = Plugin.find(__name__)
        return self._plugin

    def set_pulp_server():
        """
        Pulp server configuration
        """
        pulp = PulpServer(cfg.server.host)
        pulp.set_ssl_credentials(self.bundle.crtpath())
        set_active_server(pulp)

    def get_broker(self):
        return self.plugin.getbroker()

    def set_uuid(self):
        self.plugin.setuuid(self.bundle.getid())
