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
from datetime import datetime as dt
from datetime import timedelta as delta
from logging import getLogger

log = getLogger(__name__)



class RequestTimeout(Exception):
    """
    Request timeout.
    """

    def __init__(self, sn):
        Exception.__init__(self, sn)


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

    def send(self, qid, request, **any):
        """
        Send the request..
        @param qid: The destination queue id.
        @type qid: str
        @param request: A request to send.
        @type request: object
        @keyword any: Any (extra) data.
        """
        pass

    def broadcast(self, qids, request, **any):
        """
        Broadcast the request.
        @param qids: A list of destination queue ids.
        @type qids: [str,..]
        @param request: A request to send.
        @type request: object
        @keyword any: Any (extra) data.
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

    def send(self, qid, request, **any):
        """
        Send the request then read the reply.
        @param qid: The destination queue id.
        @type qid: str
        @param request: A request to send.
        @type request: object
        @keyword any: Any (extra) data.
        @return: The result of the request.
        @rtype: object
        @raise Exception: returned by the peer.
        """
        replyto = self.producer.queueAddress(self.producer.id)
        sn = self.producer.send(
            qid,
            replyto=replyto,
            request=request,
            **any)
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
            raise RequestTimeout(sn)
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

    def send(self, qid, request, **any):
        """
        Send the specified request and redirect the reply to the
        queue for the specified reply I{correlation} tag.
        @param qid: The destination queue id.
        @type qid: str
        @param request: A request to send.
        @type request: object
        @keyword any: Any (extra) data.
        @return: The request serial number.
        @rtype: str
        """
        replyto = \
            self.producer.queueAddress(self.tag)
        sn = self.producer.send(
                qid,
                replyto=replyto,
                request=request,
                **any)
        return sn

    def broadcast(self, qids, request, **any):
        """
        Send the specified request and redirect the reply to the
        queue for the specified reply I{correlation} tag.
        @param qids: A list of destination queue ids.
        @type qids: [str,..]
        @param request: A request to send.
        @type request: object
        @keyword any: Any (extra) data.
        """
        replyto = \
            self.producer.queueAddress(self.tag)
        sns = self.producer.broadcast(
                qids,
                replyto=replyto,
                request=request,
                **any)
        return sns


class Window:
    """
    Represents a maintenance (time) window.
    @cvar FORMAT: The datetime format. ISO 8601
    @type FORMAT: str
    @ivar begin: The window beginning datetime
    @type begin: L{dt}
    @ivar end: The window ending datetime
    @type end: L{dt}
    """

    FORMAT = '%Y-%m-%dT%H:%M:%S'

    @classmethod
    def window(cls, begin=None, **duration):
        """
        Build a window based on a beginning datetime and a duration.
        @param begin: The window beginning datetime
        @type begin: L{dt}
        @keyword duration: The diration:
          One of:
            - days
            - seconds
            - minutes
            - hours
            - weeks
        """
        begin = (begin or dt.utcnow() )
        end = begin+delta(**duration)
        return Window(begin, end)

    def __init__(self, begin, end):
        """
        @param begin: The (inclusive) beginning datetime
        @type begin: L{dt}
        @param end: The (inclusive) ending datetime
        @type end: L{dt}
        """
        self.begin = begin
        self.end = end

    def dump(self):
        """
        Dump to JSON string.
        @return: A json string.
        @rtype: str
        """
        begin = self.begin.strftime(self.FORMAT)
        end = self.end.strftime(self.FORMAT)
        env = Envelope(begin=begin, end=end)
        return env.dump()

    def load(self, s):
        """
        Load using a json string.
        @param s: A json encoded string.
        @type s: str
        """
        env = Envelope()
        env.load(s)
        self.begin = dt.strptime(env.begin, self.FORMAT)
        self.end = dt.strptime(env.end, self.FORMAT)

    def match(self):
        """
        Get whether the current datetime (UTC) falls
        within the window.
        @return: True when matched.
        @rtype: bool
        """
        now = dt.utcnow()
        return ( now >= self.begin and now <= self.end )

    def future(self):
        """
        Get whether window is in the future.
        @return: True if I{begin} > I{utcnow()}.
        @rtype: bool
        """
        now = dt.utcnow()
        return ( now < self.begin )

    def past(self):
        """
        Get whether window is in the past.
        @return: True if I{utcnow()} > I{end}.
        @rtype: bool
        """
        now = dt.utcnow()
        return ( now > self.end )

    def __str__(self):
        return self.dump()
