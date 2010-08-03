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
from pmf.endpoint import Endpoint
from qpid.messaging import Message
from logging import getLogger

log = getLogger(__name__)


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
        @return: The message serial number.
        @rtype: str
        """
        sn = getuuid()
        envelope = Envelope(sn=sn, version=version, origin=self.id)
        envelope.update(body)
        message = Message(envelope.dump())
        sender = self.session().sender(address)
        message = Message(envelope.dump())
        sender.send(message);
        log.info('{%s} sent:(%s)\n%s', self.id, address, envelope)
        return sn

    def broadcast(self, addrlist, **body):
        """
        Broadcast a message to (N) queues.
        @param addrlist: A list of AMQP address.
        @type addrlist: [str,..]
        @keyword body: envelope body.
        @return: A list of (addr,sn).
        @rtype: list
        """
        sns = []
        for addr in addrlist:
            sn = Producer.send(self, addr, **body)
            sns.append((addr,sn))
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
        @keyword body: Envelope body.
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
        @keyword body: Envelope body.
        @return: A list of (qid,sn).
        @rtype: list
        """
        lst = []
        for qid in qids:
            lst.append(self.queueAddress(qid))
        sns = []
        for addr, sn in Producer.broadcast(self, lst, **body):
            qid = addr.split(';', 1)[0]
            sns.append((qid,sn))
        return sns


class TopicProducer(Producer):
    """
    An AMQP (abstract) topic producer.
    """

    def send(self, topic, **body):
        """
        Send a message.
        @param topic: An AMQP topic and (optional) subject.
            format: topic
            (or)
            format: topic/subject
        @type topic: str
        @keyword body: envelope body.
        """
        address = self.topicAddress(topic)
        return Producer.send(self, address, **body)


class EventProducer(TopicProducer):
    """
    An AMQP event producer.
    """

    def send(self, subject, event):
        """
        Send a message to the consumer.
        @param subject: An AMQP subject.
        @type subject: str
        @param event: An event body.
        @type event: str
        """
        topic = 'event/%s' % subject
        TopicProducer.send(self, topic, event=event)
