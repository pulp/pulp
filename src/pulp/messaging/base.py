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

from pulp.messaging import *
from pulp.messaging.stub import Stub
from pulp.messaging.decorators import Remote
from pulp.messaging.dispatcher import Dispatcher
from pulp.messaging.window import Window
from pulp.messaging.policy import *
from new import classobj
from logging import getLogger

log = getLogger(__name__)



class Agent:
    """
    The agent base provides a dispatcher and automatic
    registration of methods based on decorators.
    @ivar consumer: A qpid consumer.
    @type consumer: L{pulp.messaging.Consumer}
    """

    def __init__(self, consumer):
        """
        Construct the L{Dispatcher} using the specified
        AMQP I{consumer} and I{start} the AMQP consumer.
        @param consumer: A qpid consumer.
        @type consumer: L{pulp.messaging.Consumer}
        """
        dispatcher = Dispatcher()
        dispatcher.register(*Remote.classes, **Remote.aliases)
        consumer.start(dispatcher)
        self.consumer = consumer

    def close(self):
        """
        Close and release all resources.
        """
        self.consumer.close()


class Container:
    """
    The stub container base
    @ivar __id: The peer ID.
    @type __id: str
    @ivar __producer: An AMQP producer.
    @type __producer: L{pulp.messaging.producer.Producer}
    @ivar __stubs: A list of L{Stub} objects.
    @type __stubs: [L{Stub},..]
    @ivar __options: Container options.
    @type __options: L{Options}
    """

    def __init__(self, id, producer, **options):
        """
        @param id: The peer ID.
        @type id: str
        @param producer: An AMQP producer.
        @type producer: L{pulp.messaging.producer.Producer}
        @param options: keyword options.
        @type options: dict
        """
        self.__id = id
        self.__options = Options(window=Window(), timeout=90)
        self.__stubs = []
        self.__options.update(options)
        self.__setmethod(producer)

    def __setmethod(self, producer):
        """
        Set the request method based on options.
        The selected method is added to I{options}.
        @param producer: An AMQP producer.
        @type producer: L{pulp.messaging.producer.Producer}
        """
        if self.__async():
            ctag = self.__options.ctag
            self.__options.method = Asynchronous(producer, ctag)
        else:
            timeout = int(self.__options.timeout)
            self.__options.method = Synchronous(producer, timeout)

    def __destination(self):
        """
        Get the stub destination(s).
        @return: Either a queue destination or a list of queues.
        @rtype: list
        """
        if isinstance(self.__id, (list,tuple)):
            queues = []
            for d in self.__id:
                queues.append(Queue(d))
            return queues
        else:
            return Queue(self.__id)

    def __async(self):
        """
        Get whether an I{asynchronous} request method
        should be used based on selected options.
        @return: True if async.
        @rtype: bool
        """
        if ( self.__options.ctag
             or self.__options.async ):
            return True
        return isinstance(self.__id, (list,tuple))
    
    def __getattr__(self, name):
        """
        Add stubs found in the I{stubs} dictionary.
        Each is added as an attribute matching the dictionary key.
        """
        destination = self.__destination()
        subclass = classobj(name, (Stub,), {})
        return subclass(destination, self.__options)

    def __str__(self):
        return '{%s} opt:%s' % (self.__id, str(self.__options))
