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
Defined AMQP broker objects.
"""

from pmf import *
from qpid.messaging import Connection
from logging import getLogger

log = getLogger(__name__)


class Broker:
    """
    Represents an AMQP broker.
    @cvar domain: A list dict of brokers.
    @type domain: dict
    @ivar url: The broker's url.
    @type url: L{URL}
    @ivar cacert: Path to a PEM encoded file containing
        the CA certificate used to validate the server certificate.
    @type cacert: str
    @ivar clientcert: Path to a PEM encoded file containing
        the private key & certificate used for client authentication.
    @type clientcert: str
    """

    domain = {}

    @classmethod
    def add(cls, broker):
        """
        Add a broker to the domain.
        @param broker: A broker to add
        @type broker: L{Broker}
        """
        key = broker.url
        cls.domain[key] = broker

    @classmethod
    def get(cls, url):
        """
        Get a broker from the domain by I{url}.
        Created and added if not found.
        @param url: A broker url
        @type url: L{URL}
        @return: The requested broker.
        @rtype: L{Broker}
        """
        if not isinstance(url, URL):
            url = URL(url)
        b = cls.domain.get(url)
        if not b:
            b = Broker(url)
            cls.add(b)
        return b

    def __init__(self, url):
        """
        @param url: The broker url <transport>://<host>:<port>.
        @type url: str
        """
        if isinstance(url, URL):
            self.url = url
        else:
            self.url = URL(url)
        self.cacert = None
        self.clientcert = None
        self.connection = None

    def id(self):
        """
        Get broker identifier.
        @return: The broker I{simple} url.
        @rtype: str
        """
        return self.url.simple()

    def connect(self):
        """
        Connect to the broker.
        @return: The AMQP connection object.
        @rtype: I{Connection}
        """
        if self.connection is None:
            url = self.url.simple()
            transport = self.url.transport
            log.info('connecting:\n%s', self)
            con = Connection(url=url, reconnect=True, transport=transport)
            con.attach()
            log.info('{%s} connected to AMQP', self.id())
            self.connection = con
        else:
            con = self.connection
        return con

    def close(self):
        """
        Close the connection to the broker.
        """
        try:
            self.connection.close()
        except:
            log.exception(str(self))

    def __str__(self):
        s = []
        s.append('{%s}:' % self.id())
        s.append('transport=%s' % self.url.transport.upper())
        s.append('host=%s' % self.url.host)
        s.append('port=%d' % self.url.port)
        s.append('cacert=%s' % self.cacert)
        s.append('clientcert=%s' % self.clientcert)
        return '\n'.join(s)


class URL:
    """
    Represents a QPID broker URL.
    @ivar transport: A qpid transport.
    @type transport: str
    @ivar host: The host.
    @type host: str
    @ivar port: The tcp port.
    @type port: int
    """

    @classmethod
    def split(cls, s):
        """
        Split the url string.
        @param s: A url string format: <transport>://<host>:<port>.
        @type s: str
        @return: The url parts: (transport, host, port)
        @rtype: tuple
        """
        transport, hp = cls.spliturl(s)
        host, port = cls.splitport(hp)
        return (transport, host, port)

    @classmethod
    def spliturl(cls, s):
        """
        Split the transport and url parts.
        @param s: A url string format: <transport>://<host>:<port>.
        @type s: str
        @return: The urlparts: (transport, hostport)
        @rtype: tuple
        """
        part = s.split('://', 1)
        if len(part) > 1:
            transport, hp = (part[0], part[1])
        else:
            transport, hp = ('tcp', part[0])
        return (transport, hp)

    @classmethod
    def splitport(cls, s, d=5672):
        """
        Split the host and port.
        @param s: A url string format: <host>:<port>.
        @type s: str
        @return: The urlparts: (host, port)
        @rtype: tuple
        """
        part = s.split(':')
        host = part[0]
        if len(part) < 2:
            port = d
        else:
            port = part[1]
        return (host, int(port))

    def simple(self):
        """
        Get the I{simple} string representation: <host>:<port>
        @return: "<host>:<port>"
        @rtype: str
        """
        return '%s:%d' % (self.host, self.port)

    def __init__(self, s):
        """
        @param s: A url string format: <transport>://<host>:<port>.
        @type s: str
        """
        self.transport,\
            self.host,\
            self.port = self.split(s)

    def __hash__(self):
        return hash(self.simple())

    def __eq__(self, other):
        return ( self.simple() == other.simple() )

    def __str__(self):
        return '%s://%s:%d' % \
            (self.transport,
             self.host,
             self.port)