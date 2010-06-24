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
from qpid.connection import Connection
from qpid.datatypes import Message
from qpid.queue import Empty


class Producer(Endpoint):
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

    def __init__(self, consumerid, host='localhost', port=5672):
        """
        @param consumerid: The (target) consumer ID.
        @type consumerid: str
        @param host: The fqdn or IP of the QPID broker.
        @type host: str
        @param port: The port of the QPID broker.
        @type port: short
        """
        sid = getuuid()
        socket = connect(host, port)
        connection = Connection(sock=socket)
        connection.start()
        session = connection.session(sid)
        session.queue_declare(queue=sid, exclusive=True)
        session.exchange_bind(
            exchange="amq.direct",
            queue=sid,
            binding_key=sid)
        session.message_subscribe(queue=sid, destination=sid)
        queue = session.incoming(sid)
        queue.start()
        self.consumerid = consumerid
        self.sid = sid
        self.queue = queue
        Endpoint.__init__(self, session)

    def send(self, content, sync=True):
        """
        Send a message to the consumer.
        @param content: The json encoded payload.
        @type content: str
        @param sync: Flag to indicate synchronous.
            When true the I{replyto} is set to our I{sid} and
            to (block) read the reply queue.
        @type sync: bool
        """
        sn = getuuid()
        headers = dict(consumerid=self.consumerid)
        mp = self.session.message_properties()
        mp.application_headers=headers
        envelope = Envelope(sn=sn, payload=content)
        if sync:
            envelope.replyto = ("amq.direct", self.sid)
        msg = Message(mp, envelope.dump())
        self.session.message_transfer(destination='amq.match', message=msg)
        if sync:
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
            self.acceptmessage(message.id)
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
            message = self.queue.get(timeout=90)
            envelope = Envelope()
            envelope.load(message.body)
            if sn == envelope.sn:
                result = (message, envelope)
                break
            else:
                self.acceptmessage(message.id)
        return result
