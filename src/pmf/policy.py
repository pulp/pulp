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
Contains request delivery policies.
"""

from pmf import *
from pmf.dispatcher import Return
from pmf.consumer import QueueReader


class RequestMethod:
    """
    Base class for request methods.
    @ivar producer: A queue producer.
    @type producer: L{pmf.producer.QueueProducer}
    """

    def __init__(self, producer):
        """
        @param producer: A queue producer.
        @type producer: L{pmf.producer.QueueProducer}
        """
        self.producer = producer

    def send(self, qid, request):
        """
        Send the request..
        @param qid: The destination queue id.
        @type qid: str
        @param request: A request to send.
        @type request: any
        """
        pass

    def broadcast(self, qids, request):
        """
        Broadcast the request.
        @param qids: A list of destination queue ids.
        @type qids: [str,..]
        @param request: A request to send.
        @type request: any
        """
        pass

    def close(self):
        """
        Close and release all resources.
        """
        self.producer.close()


class Synchronous(RequestMethod):
    """
    The synchronous request method.
    This method blocks until a reply is received.
    @ivar reader: A queue reader used to read the reply.
    @type reader: L{pmf.consumer.QueueReader}
    """

    def __init__(self, producer):
        """
        @param producer: A queue producer.
        @type producer: L{pmf.producer.QueueProducer}
        """
        RequestMethod.__init__(self, producer)
        reader = QueueReader(
            self.producer.id,
            self.producer.host,
            self.producer.port)
        reader.start()
        self.reader = reader

    def send(self, qid, request):
        """
        Send the request then read the reply.
        @param qid: The destination queue id.
        @type qid: str
        @param request: A request to send.
        @type request: any
        @return: The result of the request.
        @rtype: any
        @raise Exception: returned by the peer.
        """
        replyto = self.producer.queueAddress(self.producer.id)
        sn = self.producer.send(
            qid,
            replyto=replyto,
            request=request)
        return self.__getreply(sn)

    def __getreply(self, sn):
        """
        Get the reply matched by serial number.
        @param sn: The request serial number.
        @type sn: str
        @return: The matched reply envelope.
        @rtype: L{Envelope}
        """
        envelope = self.reader.search(sn)
        if not envelope:
            return
        reply = Return(envelope.result)
        self.reader.ack()
        if reply.succeeded():
            return reply.retval
        else:
            raise Exception, reply.exval


class Asynchronous(RequestMethod):
    """
    The asynchronous request method.
    """

    def __init__(self, producer, tag=None):
        """
        @param producer: A queue producer.
        @type producer: L{pmf.producer.QueueProducer}
        @param tag: A reply I{correlation} tag.
        @type tag: str
        """
        RequestMethod.__init__(self, producer)
        self.tag = tag

    def send(self, qid, request):
        """
        Send the specified request and redirect the reply to the
        queue for the specified reply I{correlation} tag.
        @param qid: The destination queue id.
        @type qid: str
        @param request: A request to send.
        @type request: any
        @return: The request serial number.
        @rtype: str
        """
        replyto = \
            self.producer.queueAddress(self.tag)
        sn = self.producer.send(
                qid,
                replyto=replyto,
                request=request)
        return sn

    def broadcast(self, qids, request):
        """
        Send the specified request and redirect the reply to the
        queue for the specified reply I{correlation} tag.
        @param qids: A list of destination queue ids.
        @type qids: [str,..]
        @param request: A request to send.
        @type request: anyr
        """
        replyto = \
            self.producer.queueAddress(self.tag)
        sns = self.producer.broadcast(
                qids,
                replyto=replyto,
                request=request)
        return sns
