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
from time import sleep

class Endpoint:
    """
    Base class for QPID endpoint.
    @ivar id: The unique AMQP session ID.
    @type id: str
    @ivar connecton: An AMQP connection.
    @type connecton: L{qpid.messaging.Connection}
    @ivar session: An AMQP session.
    @type session: L{qpid.messaging.Session}
    """
    
    def __init__(self, id=getuuid(), host='localhost', port=5672):
        """
        @param host: The broker fqdn or IP.
        @type host: str
        @param port: The broker port.
        @type port: str
        """
        self.id = id
        self.connection = Connection(host, port)
        self.session = None
        self.connect()
        self.open()

    def connect(self):
        """
        Connection to the broker.
        @return: The connection.
        @rtype: L{Connection}
        """
        while True:
            try:
                self.connection.connect()
                self.connection.start()
                break
            except Exception, e:
                if self.mustConnect():
                    sleep(3)
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
        try:
            self.session.stop()
            self.connection.close()
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
        return '%s;{create:always}' % name

    def topicAddress(self, topic):
        """
        Get a QPID topic address.
        @param topic: The topic name.
        @type topic: str
        @return: A QPID address.
        @rtype: str
        """
        return topic


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
