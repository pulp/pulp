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
Agent base classes.
"""

from pmf import *
from pmf import decorators
from pmf.dispatcher import Dispatcher
from qpid.messaging import Connection
from qpid.messaging import Message
from time import sleep
from logging import getLogger

log = getLogger(__name__)


class Endpoint:
    """
    Base class for QPID endpoint.
    @cvar connecton: An AMQP connection.
    @type connecton: L{qpid.messaging.Connection}
    @ivar id: The unique AMQP session ID.
    @type id: str
    @ivar session: An AMQP session.
    @type session: L{qpid.messaging.Session}
    """
    
    connections = {}

    @classmethod
    def shutdown(cls):
        """
        Shutdown all connections.
        """
        for con in cls.connections.values():
            con.close()
        cls.connections = {}

    def __init__(self, id=getuuid(), host='localhost', port=5672):
        """
        @param host: The broker fqdn or IP.
        @type host: str
        @param port: The broker port.
        @type port: str
        """
        self.id = id
        self.host = host
        self.port = port
        self.__session = None
        self.connect()
        self.open()

    def connection(self):
        """
        Get cached connection based on host & port.
        @return: The global connection.
        @rtype: L{qpid.messaging.Connection}
        """
        key = (self.host, self.port)
        con = self.connections.get(key)
        if con is None:
            con = Connection(self.host, self.port)
            self.connections[key] = con
        return con

    def session(self):
        """
        Get a session for the open connection.
        @return: An open session.
        @rtype: L{qpid.messaging.Session}
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

    def connect(self):
        """
        Connection to the broker.
        @return: The connection.
        @rtype: L{Connection}
        """
        while True:
            try:
                log.info('%s, connecting', self)
                con = self.connection()
                con.connect()
                con.start()
                log.info('%s, connected', self)
                break
            except Exception, e:
                log.exception(e)
                if self.mustConnect():
                    sleep(10)
                else:
                    raise e

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

    def mustConnect(self):
        """
        Get whether the endpoint must connect.
        When true, calls to connect() will block until a connection
        can be successfully made.
        @return: True/False
        @rtype: bool
        """
        return False

    def queueAddress(self, name):
        """
        Get a QPID queue address.
        @param name: The queue name.
        @type name: str
        @return: A QPID address.
        @rtype: str
        """
        return '%s;{create:always,node:{type:queue}}' % name

    def topicAddress(self, topic):
        """
        Get a QPID topic address.
        @param topic: The topic name.
        @type topic: str
        @param subject: The subject.
        @type subject: str
        @return: A QPID address.
        @rtype: str
        """
        return '%s;{create:always,node:{type:topic}}' % topic

    def __del__(self):
        self.close()
        
    def __str__(self):
        return 'Endpoint id:%s broker @ %s:%s' % \
            (self.id, self.host, self.port)


class Consumer(Endpoint):
    """
    An AMQP (abstract) consumer.
    """
    def mustConnect(self):
        return True

    def start(self):
        """
        Start processing messages on the queue.
        """
        self.receiver.listen(self.received)
        self.receiver.start()

    def stop(self):
        """
        Stop processing requests.
        """
        try:
            self.receiver.stop()
        except:
            pass

    def received(self, message):
        """
        Process received request.
        @param message: The received message.
        @type message: L{Message}
        """
        envelope = Envelope()
        envelope.load(message.content)
        self.dispatch(envelope)
        self.ack()

    def dispatch(self, envelope):
        """
        Dispatch received request.
        @param message: The received message.
        @type message: L{Message}
        """
        pass


class Producer(Endpoint):
    """
    An AMQP (abstract) message producer.
    """

    def open(self):
        """
        Open and configure the producer.
        """
        self.session()

    def send(self, address, **body):
        """
        Send a message.
        @param address: An AMQP address.
        @type address: str
        @keyword body: envelope body.
        """
        sn = getuuid()
        envelope = Envelope(sn=sn)
        envelope.update(body)
        message = Message(envelope.dump())
        sender = self.session().sender(address)
        message = Message(envelope.dump())
        sender.send(message);
        return sn


class Agent:
    """
    The agent base provides a dispatcher and automatic
    registration of methods based on decorators.
    @ivar consumer: A qpid consumer.
    @type consumer: L{pmf.Consumer}
    """

    def __init__(self, consumer):
        """
        Construct the L{Dispatcher} using the specified
        AMQP I{consumer} and I{start} the AMQP consumer.
        @param consumer: A qpid consumer.
        @type consumer: L{pmf.Consumer}
        """
        dispatcher = Dispatcher()
        dispatcher.register(*decorators.remoteclasses)
        consumer.start(dispatcher)
        self.consumer = consumer

    def close(self):
        """
        Close and release all resources.
        """
        self.consumer.close()


class AgentProxy:
    """
    The proxy base
    @ivar producer: A qpid producer.
    @type producer: L{pmf.Producer}
    """

    def __init__(self, producer):
        """
        @param producer: A qpid producer.
        @type producer: L{pmf.Producer}}
        """
        self.producer = producer

    def close(self):
        """
        Close and release all resources.
        """
        self.producer.close()
