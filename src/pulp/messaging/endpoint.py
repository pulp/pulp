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
AMQP endpoint base classes.
"""

from pulp.messaging import *
from pulp.messaging.broker import Broker
from pulp.messaging.transport import SSLTransport
from qpid.messaging import Connection
from time import sleep
from logging import getLogger

log = getLogger(__name__)


class Endpoint:
    """
    Base class for QPID endpoint.
    @cvar connectons: An AMQP connection.
    @type connectons: L{Connection}
    @ivar uuid: The unique endpoint id.
    @type uuid: str
    @ivar __session: An AMQP session.
    @type __session: qpid.messaging.Session
    """

    LOCALHOST = 'tcp://localhost:5672'

    @classmethod
    def shutdown(cls):
        """
        Shutdown all connections.
        """
        for broker in Broker.domain.values():
            try:
                broker.close()
            except:
                pass

    def __init__(self, uuid=getuuid(), url=LOCALHOST):
        """
        @param uuid: The endpoint uuid.
        @type uuid: str
        @param url: The broker url <transport>://<user>/<pass>@<host>:<port>.
        @type url: str
        """
        self.uuid = uuid
        self.url = url
        self.__session = None
        self.open()

    def id(self):
        """
        Get the endpoint id
        @return: The id.
        @rtype: str
        """
        return self.uuid

    def connection(self):
        """
        Get cached connection based on I{url}.
        @return: The global connection.
        @rtype: L{Connection}
        """
        broker = Broker.get(self.url)
        con = broker.connect()
        log.info('{%s} connected to AMQP' % self.id())
        return con

    def session(self):
        """
        Get a session for the open connection.
        @return: An open session.
        @rtype: qpid.messaging.Session
        """
        if self.__session is None:
            con = self.connection()
            self.__session = con.session()
        return self.__session

    def ack(self):
        """
        Acknowledge all messages received on the session.
        """
        try:
            self.__session.acknowledge()
        except:
            pass

    def open(self):
        """
        Open and configure the endpoint.
        """
        pass

    def close(self):
        """
        Close (shutdown) the endpoint.
        """
        session = self.__session
        self.__session = None
        try:
            session.stop()
            session.close()
        except:
            pass

    def __parsedurl(self):
        urlpart = self.url.split('://', 1)
        if len(urlpart) == 1:
            return (urlpart[0], 'tcp')
        else:
            return (urlpart[0], urlpart[1])

    def __del__(self):
        self.close()

    def __str__(self):
        return 'Endpoint id:%s broker @ %s' % (self.id(), self.url)
