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
Provides async AMQP message consumer classes.
"""

from pmf import *
from pmf.dispatcher import Return
from pmf.consumer import Consumer, QueueConsumer
from logging import getLogger

log = getLogger(__name__)


class ReplyConsumer(QueueConsumer):
    """
    A request, reply consumer.
    @ivar listener: An reply listener.
    @type listener: any
    """

    def start(self, listener):
        """
        Start processing messages on the queue and
        forward to the listener.
        @param listener: A reply listener.
        @type listener: L{Listener}
        """
        self.listener = listener
        Consumer.start(self)

    def dispatch(self, envelope):
        """
        Dispatch received request.
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        """
        try:
            reply = Return(envelope.result)
            if reply.succeeded():
                self.listener.succeeded(Succeeded(envelope))
            else:
                self.listener.failed(Failed(envelope))
        except Exception, e:
            log.exception(e)


class AsyncReply:
    """
    Asynchronous request reply.
    @ivar sn: The request serial number.
    @type sn: str
    @ivar sender: Which endpoint sent the reply.
    @ivar sender: str
    @ivar any: User defined (round-tripped) data.
    @type any: object
    """
    
    def __init__(self, envelope):
        """
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        """
        self.sn = envelope.sn
        self.sender = envelope.sender
        self.any = envelope.any
        
    def throw(self):
        """
        Throw (re-raise) exceptions contained in the reply.
        """
        pass
    
    def __str__(self):
        s = []
        s.append(self.__class__.__name__)
        s.append('  sn : %s' % self.sn)
        s.append('  sender : %s' % self.sender)
        return '\n'.join(s)
        

   
class Succeeded(AsyncReply):
    """
    Successful reply to asynchronous operation.
    @ivar retval: The returned value.
    @type retval: object
    """
    
    def __init__(self, envelope):
        """
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        """
        AsyncReply.__init__(self, envelope)
        reply = Return(envelope.result)
        self.retval = reply.retval
    
    def __str__(self):
        s = []
        s.append(AsyncReply.__str__(self))
        s.append('  retval:')
        s.append(str(self.retval))
        return '\n'.join(s)
        

class Failed(AsyncReply):
    """
    Failed reply to asynchronous operation.  This reply
    indicates an exception was raised.
    @ivar retval: The returned value.
    @type retval: object
    @see: L{throw}
    """
    
    def __init__(self, envelope):
        """
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        """
        AsyncReply.__init__(self, envelope)
        reply = Return(envelope.result)
        self.exval = Exception(reply.exval)
        
    def throw(self):
        raise self.exval
    
    def __str__(self):
        s = []
        s.append(AsyncReply.__str__(self))
        s.append('  exception:')
        s.append(str(self.exval))
        return '\n'.join(s)


class Listener:
    """
    An asynchronous operation callback listener.
    """
    
    def succeeded(self, reply):
        """
        Async request succeeded.
        @param reply: The reply data.
        @type reply: L{Succeeded}.
        """
        pass
    
    def failed(self, reply):
        """
        Async request failed (raised an exception).
        @param reply: The reply data.
        @type reply: L{Failed}.
        """
        pass
