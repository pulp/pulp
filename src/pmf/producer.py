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
Contains AMQP message producer classes.
"""

from pmf import *
from pmf.base import Endpoint
from pmf.dispatcher import Return
from pmf.envelope import Envelope
from qpid.util import connect
from qpid.messaging import Message, Empty


class RequestProducer(Endpoint):
    """
    An AMQP message producer.
    @ivar consumerid: The AMQP consumer (target) queue ID.
    @type consumerid: str
    @ivar sid: The unique AMQP session ID.
    @type sid: str
    @ivar queue: The primary incoming (reply) message queue.
    @type queue: L{qpid.Queue}
    @ivar session: An AMQP session.
    @type session: L{qpid.Session}
    """

    def open(self):
        """
        Open and configure the producer.
        """
        session = self.connection.session()
        address = self.queueAddress(self.id)
        receiver = session.receiver(address)
        receiver.start()
        self.receiver = receiver
        self.session = session

    def send(self, consumerid, content, synchronous=True):
        """
        Send a message to the consumer.
        @param content: The json encoded payload.
        @type content: str
        @param synchronous: Flag to indicate synchronous.
            When true the I{replyto} is set to our I{sid} and
            to (block) read the reply queue.
        @type synchronous: bool
        """
        sn = getuuid()
        envelope = Envelope(sn=sn, payload=content)
        if synchronous:
            envelope.replyto = self.queueAddress(self.id)
        message = Message(envelope.dump())
        address = self.queueAddress(consumerid)
        sender = self.session.sender(address)
        message = Message(envelope.dump())
        sender.send(message);
        if synchronous:
            return self._getreply(sn)
        else:
            return None

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
            self.session.acknowledge()
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
                self.session.acknowledge()
        return result


class EventProducer:
    """
    An AMQP event producer.
    @ivar session: An AMQP session.
    @type session: L{qpid.Session}
    """
    pass