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
Provides AMQP message consumer classes.
"""

from pmf import *
from pmf.base import Endpoint
from pmf.envelope import Envelope
from qpid.messaging import Message, Empty
from qpid.exceptions import Closed

class RequestConsumer(Endpoint):
    """
    An AMQP consumer.
    @ivar queue: The primary incoming message queue.
    @type queue: L{qpid.Queue}
    @ivar session: An AMQP session.
    @type session: L{qpid.Session}
    """

    def open(self):
        """
        Open and configure the consumer.
        """
        session = self.connection.session()
        address = self.queueAddress(self.id)
        receiver = session.receiver(address)
        receiver.start()
        self.receiver = receiver
        self.session = session

    def mustConnect(self):
        return True

    def start(self, dispatcher):
        """
        Start processing messages on the queue using the
        specified dispatcher.
        @param dispatcher: An RMI dispatcher.
        @type dispatcher: L{pmf.Dispatcher}
        @return: self
        @rtype: L{Consumer}
        """
        while True:
            try:
                message = self.receiver.fetch(timeout=1)
                envelope = Envelope()
                envelope.load(message.content)
                sn = envelope.sn
                content = envelope.payload
                result = dispatcher.dispatch(content)
                self.__respond(envelope, result)
                self.session.acknowledge()
            except Closed:
                self.connect()
                self.open()
            except Empty:
                pass

    def __respond(self, request, result):
        """
        Respond to request with the specified I{content}.
        A response is send B{only} when a I{replyto} is specified
        in the I{message}.
        @param request: The request envelope.
        @type request: L{Envelope}
        @param result: A reply object.
        @type result: L{pmf.Return}
        """
        replyto = request.replyto
        if not replyto:
            return
        envelope = Envelope(sn=request.sn)
        envelope.payload = result
        sender = self.session.sender(replyto)
        message = Message(envelope.dump())
        sender.send(message);
        return self


class EventConsumer:
    """
    An AMQP consumer.
    @ivar session: An AMQP session.
    @type session: L{qpid.Session}
    """
    pass