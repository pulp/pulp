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
Contains AMQP message producer classes.
"""

from pmf import *
from pmf.base import Endpoint
from pmf.envelope import Envelope
from pmf.mode import Mode
from pmf.dispatcher import Return
from qpid.util import connect
from qpid.messaging import Message, Empty


class RequestProducer(Endpoint):
    """
    An AMQP message producer.
    @ivar receiver: The (reply) queue receiver.
    @type receiver: L{qpid.messaging.Receiver}
    """

    def open(self):
        """
        Open and configure the producer.
        """
        session = self.session()
        address = self.queueAddress(self.id)
        receiver = session.receiver(address)
        receiver.start()
        self.receiver = receiver

    def send(self, consumerid, content, mode=Mode()):
        """
        Send a message to the consumer.
        @param content: The json encoded payload.
        @type content: str
        @param mode: Flag to indicate synchronous.
            When true the I{replyto} is set to our I{sid} and
            to (block) read the reply queue.
        @type mode: bool
        """
        sn = getuuid()
        envelope = Envelope(sn=sn, mode=mode, payload=content)
        self._setreply(envelope)
        message = Message(envelope.dump())
        address = self.queueAddress(consumerid)
        sender = self.session().sender(address)
        message = Message(envelope.dump())
        sender.send(message);
        if mode.synchronous:
            return self._getreply(sn)
        else:
            return sn

    def _setreply(self, envelope):
        """
        Setup the reply based on I{mode}.
        @param envelope: A request envelope.
        @type envelope: L{Envelope}
        """
        mode = envelope.mode
        if mode.synchronous:
            mode.group = self.id
        if mode.group:
            envelope.replyto = self.queueAddress(mode.group)

    def _getreply(self, sn):
        """
        Read the reply from our reply queue.
        @param sn: The request serial number.
        @type sn: str
        @return: The json unencoded reply.
        @rtype: any
        """
        try:
            message, envelope = self._searchqueue(sn)
            if not message:
                return
            reply = Return()
            reply.load(envelope.payload)
            self.ack()
            if reply.succeeded():
                return reply.retval
            else:
                raise Exception, reply.exval
        except Empty:
            # TODO: something better for timeouts.
            pass

    def _searchqueue(self, sn):
        """
        Seach the reply queue for the envelope with
        the matching serial #.
        @param sn: The expected serial number.
        @type sn: str
        @return: (message, envelope)
        @rtype: tuple
        """
        while True:
            result = (None, None)
            message = self.receiver.fetch(timeout=90)
            envelope = Envelope()
            envelope.load(message.content)
            if sn == envelope.sn:
                result = (message, envelope)
                break
            else:
                self.ack()
        return result


class EventProducer:
    """
    An AMQP event producer.
    @ivar session: An AMQP session.
    @type session: L{qpid.Session}
    """

    def open(self):
        """
        Open and configure the producer.
        """
        self.session = session()

    def send(self, topic, event):
        """
        Send a message to the consumer.
        @param event: An event object.
        @type event: str
        """
        sn = getuuid()
        envelope = Envelope(sn=sn, payload=event)
        message = Message(envelope.dump())
        address = self.topicAddress(topic)
        sender = self.session().sender(address)
        message = Message(envelope.dump())
