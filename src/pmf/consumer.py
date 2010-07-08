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
from pmf.base import Consumer, Producer
from pmf.dispatcher import Return
from qpid.messaging import Empty


class QueueConsumer(Consumer):
    """
    An AMQP (abstract) queue consumer.
    @ivar receiver: The message receiver.
    @type receiver: L{qpid.Receiver}
    """

    def open(self):
        """
        Open and configure the consumer.
        """
        session = self.session()
        address = self.queueAddress(self.id)
        receiver = session.receiver(address)
        self.receiver = receiver


class QueueReader(QueueConsumer):

    def start(self):
        """
        Start processing messages on the queue.
        """
        self.receiver.start()

    def next(self, timeout=90):
        """
        Get the next envelope from the queue.
        @param timeout: The read timeout.
        @type timeout: int
        @return: The next envelope.
        @rtype: L{Envelope}
        """
        try:
            message = self.receiver.fetch(timeout=timeout)
            envelope = Envelope()
            envelope.load(message.content)
            return envelope
        except Empty:
            pass

    def search(self, sn, timeout=90):
        """
        Seach the reply queue for the envelope with
        the matching serial #.
        @param sn: The expected serial number.
        @type sn: str
        @param timeout: The read timeout.
        @type timeout: int
        @return: The next envelope.
        @rtype: L{Envelope}
        """
        while True:
            envelope = self.next(timeout)
            if sn == envelope.sn:
                return envelope
            else:
                self.ack()


class RequestConsumer(QueueConsumer):
    """
    An AMQP request consumer.
    @ivar receiver: The incoming message receiver.
    @type receiver: L{qpid.Queue}
    @ivar session: An AMQP session.
    @type session: L{qpid.Session}
    """

    def start(self, dispatcher):
        """
        Start processing messages on the queue using the
        specified dispatcher.
        @param dispatcher: An RMI dispatcher.
        @type dispatcher: L{pmf.Dispatcher}
        """
        self.dispatcher = dispatcher
        self.producer = Producer(host=self.host, port=self.port)
        Consumer.start(self)

    def dispatch(self, envelope):
        """
        Dispatch received request.
        @param message: The received message.
        @type message: L{Envelope}
        """
        request = envelope.request
        result = self.dispatcher.dispatch(request)
        sn = envelope.sn
        replyto = envelope.replyto
        if replyto:
            self.producer.send(replyto, sn=sn, result=result)


class TopicConsumer(Consumer):
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


class EventConsumer(TopicConsumer):
    """
    An AMQP topic consumer.
    @ivar session: An AMQP session.
    @type session: L{qpid.Session}
    """

    def dispatch(self, envelope):
        """
        Process received request.
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        """
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
