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
Provides AMQP message consumer classes.
"""

from pmf import *
from pmf.base import Endpoint
from pmf.envelope import Envelope
from pmf.dispatcher import Return
from qpid.messaging import Message, Empty
from qpid.exceptions import Closed


class RequestConsumer(Endpoint):
    """
    An AMQP request consumer.
    @ivar receiver: The incoming message receiver.
    @type receiver: L{qpid.Queue}
    @ivar session: An AMQP session.
    @type session: L{qpid.Session}
    """

    def open(self):
        """
        Open and configure the consumer.
        """
        session = self.session()
        address = self.queueAddress(self.id)
        receiver = session.receiver(address)
        self.receiver = receiver

    def mustConnect(self):
        return True

    def start(self, dispatcher):
        """
        Start processing messages on the queue using the
        specified dispatcher.
        @param dispatcher: An RMI dispatcher.
        @type dispatcher: L{pmf.Dispatcher}
        """
        self.dispatcher = dispatcher
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
        request = envelope.request
        result = self.dispatcher.dispatch(request)
        self.respond(envelope, result)
        self.ack()

    def respond(self, request, result):
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
        envelope.result = result
        sender = self.session().sender(replyto)
        message = Message(envelope.dump())
        sender.send(message);
        return self


class EventConsumer(Endpoint):
    """
    An AMQP topic consumer.
    @ivar session: An AMQP session.
    @type session: L{qpid.Session}
    """
    def open(self):
        """
        Open and configure the consumer.
        """
        session = self.session()
        address = self.topicAddress(self.id)
        receiver = session.receiver(address)
        self.receiver = receiver

    def mustConnect(self):
        return True

    def start(self):
        """
        Start listening for events.
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
        event = envelope.event
        try:
            self.notify(event)
        except:
            pass # TODO: LOG THIS BETTER
        self.ack()

    def notify(self, event):
        """
        Notify the listener that an event has been consumed.
        @param event: The received event.
        @type event: L{Event}
        """
        pass
