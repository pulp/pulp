#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Jeff Ortel <jortel@redhat.com>
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

class Agent:
    """
    The agent base provides a dispatcher and automatic
    registration of methods based on decorators.
    @ivar dispatcher: An RMI dispatcher.
    @type dispatcher: L{Dispatcher}
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
        

class Endpoint:
    """
    Base class for qpid endpoint.
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
        return '%s;{create:always}' % name
