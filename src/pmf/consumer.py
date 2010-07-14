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
from pmf.producer import Producer
from pmf.dispatcher import Return
from pmf.window import *
from pmf.store import PendingQueue, PendingReceiver
from qpid.messaging import Empty
from logging import getLogger

log = getLogger(__name__)


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
        log.info('{%s} received:\n%s', self.id, envelope)
        self.dispatch(envelope)
        self.ack()

    def dispatch(self, envelope):
        """
        Dispatch received request.
        @param envelope: The received envelope.
        @type envelope: L{Message}
        """
        pass


class QueueConsumer(Consumer):
    """
    An AMQP (abstract) queue consumer.
    @ivar receiver: The message receiver.
    @type receiver: L{qpid.messaging.Receiver}
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
            log.info('{%s} read next:\n%s', self.id, envelope)
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
        log.info('{%s} searching for: sn=%s', self.id, sn)
        while True:
            envelope = self.next(timeout)
            if not envelope:
                return
            if sn == envelope.sn:
                log.info('{%s} search found:\n%s', self.id, envelope)
                return envelope
            else:
                log.info('{%s} search discarding:\n%s', self.id, envelope)
                self.ack()


class RequestConsumer(QueueConsumer):
    """
    An AMQP request consumer.
    @ivar producer: A reply producer.
    @type producer: L{pmf.producer.QueueProducer}
    @ivar dispatcher: An RMI dispatcher.
    @type dispatcher: L{pmf.dispatcher.Dispatcher}
    """

    def start(self, dispatcher):
        """
        Start processing messages on the queue using the
        specified dispatcher.
        @param dispatcher: An RMI dispatcher.
        @type dispatcher: L{pmf.Dispatcher}
        """
        q = PendingQueue(self.id)
        self.pending = PendingReceiver(q, self)
        self.dispatcher = dispatcher
        self.producer = Producer(self.id, self.host, self.port)
        Consumer.start(self)
        self.pending.start()

    def dispatch(self, envelope):
        """
        Dispatch received request.
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        """
        try:
            self.checkwindow(envelope)
            request = envelope.request
            result = self.dispatcher.dispatch(request)
        except WindowMissed, m:
            result = Return.exception(m)
        except WindowPending:
            return
        self.sendreply(envelope, result)

    def sendreply(self, envelope, result):
        """
        Send the reply if requested.
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        @param result: The request result.
        @type result: object
        """
        sn = envelope.sn
        any = envelope.any
        replyto = envelope.replyto
        if replyto:
            self.producer.send(
                replyto,
                sn=sn,
                any=any,
                result=result)

    def checkwindow(self, envelope):
        """
        Check the window.
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        """
        window = Window(envelope.window)
        if window.future():
            pending = self.pending.queue
            pending.add(envelope)
            raise WindowPending(envelope.sn)
        if window.past():
            raise WindowMissed(envelope.sn)

    def __del__(self):
        try:
            self.pending.stop()
            self.pending.join(10)
        except:
            pass


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
        @param listener: An reply listener.
        @type listener: any
        """
        self.listener = listener
        Consumer.start(self)

    def dispatch(self, envelope):
        """
        Dispatch received request.
        @param message: The received message.
        @type message: L{Envelope}
        """
        try:
            reply = Return(envelope.result)
            if reply.succeeded():
                self.listener.succeeded(
                    envelope.sn,
                    envelope.sender,
                    reply.retval,
                    envelope.any)
            else:
                self.listener.failed(
                    envelope.sn,
                    envelope.sender,
                    reply.exval,
                    envelope.any)
        except Exception, e:
            log.exception(e)


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
        except Exception, e:
            log.exception(e)
        self.ack()

    def notify(self, event):
        """
        Notify the listener that an event has been consumed.
        @param event: The received event.
        @type event: L{Event}
        """
        pass
