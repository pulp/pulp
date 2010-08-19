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
Contains custom QPID transport classes.
"""

from pulp.messaging.broker import Broker
from ssl import wrap_socket, CERT_NONE, CERT_REQUIRED
from qpid.messaging.transports import connect, TRANSPORTS, tls
from logging import getLogger

log = getLogger(__name__)


class SSLTransport(tls):
    """
    SSL Transport.
    """

    def __init__(self, broker):
        """
        @param broker: An amqp broker.
        @type broker: L{Broker}
        """
        url = broker.url
        self.socket = connect(url.host, url.port)
        if broker.cacert:
            reqcert = CERT_REQUIRED
        else:
            reqcert = CERT_NONE
        self.tls = wrap_socket(
                self.socket,
                cert_reqs=reqcert,
                ca_certs = broker.cacert,
                certfile = broker.clientcert)
        self.socket.setblocking(0)
        self.state = None


class SSLFactory:
    """
    Factory used to create a transport.
    """

    def __call__(self, host, port):
        """
        @param host: A host or IP.
        @type host: str
        @type port: A tcp port.
        @type port: int
        """
        url = '%s:%d' % (host, port)
        broker = Broker.get(url)
        transport = SSLTransport(broker)
        return transport

#
# Install the transport.
#
TRANSPORTS['ssl'] = SSLFactory()
