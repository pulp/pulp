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
from pmf.base import Producer
from pmf.dispatcher import Return
from pmf.consumer import QueueReader


class QueueProducer(Producer):
    """
    An AMQP (abstract) queue producer.
    """

    def send(self, qid, **body):
        """
        Send a message.
        @param qid: An AMQP queue ID.
        @type qid: str
        @keyword body: envelope body.
        """
        address = self.queueAddress(qid)
        return Producer.send(self, address, **body)


class RequestProducer(QueueProducer):
    """
    An AMQP message producer.
    @ivar reader: The (reply) queue reader.
    @type reader: L{QueueReader}
    """

    def open(self):
        """
        Open and configure the producer.
        """
        self.session()
        self.reader = QueueReader(self.id, self.host, self.port)
        self.reader.start()

    def send(self, qid, request, synchronous=True):
        """
        Send a message to the consumer.
        @param qid: The destination queue id.
        @type qid: str
        @param request: The json encoded request.
        @type request: str
        @param synchronous: Flag to indicate synchronous.
            When true the I{replyto} is set to our I{sid} and
            to (block) read the reply queue.
        @type synchronous: bool
        """
        if synchronous:
            replyto = self.queueAddress(self.id)
        else:
            replyto = None
        sn = QueueProducer.send(self, qid, replyto=replyto, request=request)
        if synchronous:
            return self.__getreply(sn)
        else:
            return sn

    def __getreply(self, sn):
        """
        Read the reply from our reply queue.
        @param sn: The request serial number.
        @type sn: str
        @return: The json unencoded reply.
        @rtype: any
        """
        envelope = self.reader.search(sn)
        if not envelope:
            return
        reply = Return(envelope.result)
        self.ack()
        if reply.succeeded():
            return reply.retval
        else:
            raise Exception, reply.exval


class TopicProducer(Producer):
    """
    An AMQP (abstract) topic producer.
    """

    def send(self, topic, **body):
        """
        Send a message.
        @param topic: An AMQP topic.
        @type topic: str
        @keyword body: envelope body.
        """
        address = self.topicAddress(topic)
        return Producer.send(self, address, **body)


class EventProducer(TopicProducer):
    """
    An AMQP event producer.
    """

    def send(self, topic, event):
        """
        Send a message to the consumer.
        @param topic: An AMQP topic.
        @type topic: str
        @param event: An event body.
        @type event: str
        """
        TopicProducer.send(self, topic, event=event)
