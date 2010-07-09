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
from qpid.messaging import Message


class Producer(Endpoint):
    """
    An AMQP (abstract) message producer.
    """

    def open(self):
        """
        Open and configure the producer.
        """
        pass

    def send(self, address, **body):
        """
        Send a message.
        @param address: An AMQP address.
        @type address: str
        @keyword body: envelope body.
        """
        sn = getuuid()
        envelope = Envelope(sn=sn)
        envelope.update(body)
        message = Message(envelope.dump())
        sender = self.session().sender(address)
        message = Message(envelope.dump())
        sender.send(message);
        return sn

    def broadcast(self, addrlist, **body):
        """
        Broadcast a message to (N) queues.
        @param addrlist: A list of AMQP address.
        @type addrlist: [str,..]
        @keyword body: envelope body.
        """
        sns = []
        for addr in addrlist:
            sn = Producer.send(self, addr, **body)
            sns.append(sn)
        return sns


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
        @return: The sent envelope serial number.
        @rtype: str
        """
        address = self.queueAddress(qid)
        return Producer.send(self, address, **body)

    def broadcast(self, qids, **body):
        """
        Broadcast a message to (N) queues.
        @param qids: An list of AMQP queue IDs.
        @type qids: [qid,..]
        @keyword body: envelope body.
        """
        lst = []
        for qid in qids:
            lst.append(self.queueAddress(qid))
        return Producer.broadcast(self, lst, **body)


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
