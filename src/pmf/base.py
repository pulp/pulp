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
from pmf.decorators import Remote
from pmf.dispatcher import Dispatcher
from pmf.window import Window
from pmf.policy import *
from logging import getLogger

log = getLogger(__name__)



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
        dispatcher.register(*Remote.classes)
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
    @type __producer: L{pmf.producer.Producer}
    @ivar __stubs: A list of L{Stub} objects.
    @type __stubs: [{Stub,..]
    @ivar __options: Container options.
    @type __options: L{Options}
    """

    def __init__(self, id, producer, **options):
        """
        @ivar id: The peer ID.
        @type id: str
        @ivar producer: An AMQP producer.
        @type producer: L{pmf.producer.Producer}
        @ivar options: keyword options.
        @type options: dict
        """
        self.__id = id
        self.__options = Options(window=Window())
        self.__stubs = []
        self.__options.update(options)
        self.__setmethod(producer)
        self.__addstubs()

    def __setmethod(self, producer):
        """
        Set the request method based on options.
        The selected method is added to I{options}.
        @param producer: An AMQP producer.
        @type producer: L{pmf.producer.Producer}
        """
        if self.__async():
            ctag = self.__options.ctag
            self.__options.method = Asynchronous(producer, ctag)
        else:
            self.__options.method = Synchronous(producer)

    def __addstubs(self):
        """
        Add stubs found in the I{stubs} dictionary.
        Each is added as an attribute matching the dictionary key.
        """
        for ns, sclass in Remote.stubs.items():
            stub = sclass(self.__id, self.__options)
            setattr(self, ns, stub)
            self.__stubs.append(stub)

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

    def __str__(self):
        return '{%s} opt:%s' % (self.__id, str(self.__options))
