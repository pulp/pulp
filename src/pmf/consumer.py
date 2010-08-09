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
from pmf.endpoint import Endpoint
from pmf.producer import Producer
from pmf.dispatcher import Return
from pmf.window import *
from pmf.store import PendingQueue, PendingReceiver
from qpid.messaging import Empty
from threading import Thread
from logging import getLogger

log = getLogger(__name__)


class ReceiverThread(Thread):
    """
    Consumer (worker) thread.
    @ivar __run: The main run/read flag.
    @type __run: bool
    @ivar consumer: A consumer that is notified when
        messages are read.
    @type consumer: L{Consumer}
    """
    
    def __init__(self, consumer):
        """
        @param consumer: A consumer that is notified when
            messages are read.
        @type consumer: L{Consumer}
        """
        self.__run = True
        self.consumer = consumer
        Thread.__init__(self, name=consumer.id())

    def run(self):
        """
        Messages are read from consumer.receiver and
        dispatched to the consumer.received().
        """
        m = None
        receiver = self.consumer.receiver
        while self.__run:
            try:
                m = receiver.fetch(timeout=1)
                self.consumer.received(m)
            except Empty:
                pass
            except Exception:
                log.error('failed:\n%s', m, exc_info=True)
            
    def stop(self):
        """
        Stop reading the receiver and terminate
        the thread.
        """
        self.__run = False


class Consumer(Endpoint):
    """
    An AMQP (abstract) consumer.
    """

    def __init__(self, destination, *other):
        """
        @param destination: The destination to consumer.
        @type destination: L{Destination}
        """
        self.destination = destination
        Endpoint.__init__(self, *other)

    def id(self):
        """
        Get the endpoint id
        @return: The destination (simple) address.
        @rtype: str
        """
        return repr(self.destination)

    def address(self):
        """
        Get the AMQP address for this endpoint.
        @return: The AMQP address.
        @rtype: str
        """
        return str(self.destination)

    def open(self):
        """
        Open and configure the consumer.
        """
        session = self.session()
        address = self.address()
        log.info('{%s} opening %s', self.id(), address)
        receiver = session.receiver(address)
        self.receiver = receiver

    def start(self):
        """
        Start processing messages on the queue.
        """
        self.thread = ReceiverThread(self)
        self.thread.start()

    def stop(self):
        """
        Stop processing requests.
        """
        try:
            self.thread.stop()
        except:
            pass

    def join(self):
        """
        Join the worker thread.
        """
        self.thread.join()

    def received(self, message):
        """
        Process received request.
        @param message: The received message.
        @type message: L{qpid.messaging.Message}
        """
        envelope = Envelope()
        subject = self.__subject(message)
        envelope.load(message.content)
        if subject:
            envelope.subject = subject
        log.info('{%s} received:\n%s', self.id(), envelope)
        if self.valid(envelope):
            self.dispatch(envelope)
        self.ack()

    def valid(self, envelope):
        """
        Check to see if the envelope is valid.
        @param envelope: The received envelope.
        @type envelope: L{qpid.messaging.Message}
        """
        valid = True
        if envelope.version != version:
            valid = False
            log.info('{%s} version mismatch (discarded):\n%s',
                self.id(), envelope)
        return valid

    def dispatch(self, envelope):
        """
        Dispatch received request.
        @param envelope: The received envelope.
        @type envelope: L{qpid.messaging.Message}
        """
        pass

    def __subject(self, message):
        """
        Extract the message subject.
        @param message: The received message.
        @type message: L{qpid.messaging.Message}
        @return: The message subject
        @rtype: str
        """
        return message.properties.get('qpid.subject')


class Reader(Consumer):

    def start(self):
        pass

    def stop(self):
        pass

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
            log.info('{%s} read next:\n%s', self.id(), envelope)
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
        log.info('{%s} searching for: sn=%s', self.id(), sn)
        while True:
            envelope = self.next(timeout)
            if not envelope:
                return
            if sn == envelope.sn:
                log.info('{%s} search found:\n%s', self.id(), envelope)
                return envelope
            else:
                log.info('{%s} search discarding:\n%s', self.id(), envelope)
                self.ack()


class RequestConsumer(Consumer):
    """
    An AMQP request consumer.
    @ivar producer: A reply producer.
    @type producer: L{pmf.producer.Producer}
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
        q = PendingQueue(self.id())
        self.pending = PendingReceiver(q, self)
        self.dispatcher = dispatcher
        self.producer = Producer(self.url)
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
            self.sendstarted(envelope)
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

    def sendstarted(self, envelope):
        """
        Send the a status update if requested.
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        """
        sn = envelope.sn
        any = envelope.any
        replyto = envelope.replyto
        if replyto:
            self.producer.send(
                replyto,
                sn=sn,
                any=any,
                status='started')

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


class EventConsumer(Consumer):
    """
    An AMQP event consumer.
    """

    def __init__(self, subject, name=None, *other):
        """
        @param subject: An event subject.
        @type subject: str
        """
        topic = Topic('event', subject, name)
        Consumer.__init__(self, topic, *other)

    def dispatch(self, envelope):
        """
        Process received request.
        @param envelope: The received envelope.
        @type envelope: L{Envelope}
        """
        try:
            subject = envelope.subject
            body = envelope.event
            self.notify(subject, body)
        except Exception, e:
            log.exception(e)
        self.ack()

    def notify(self, subject, body):
        """
        Notify the listener that an event has been consumed.
        @param subject: The event subject.
        @type subject: str
        @param body: The event body.
        @type body: any
        """
        pass
