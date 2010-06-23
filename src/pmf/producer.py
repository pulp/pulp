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
from pmf.dispatcher import Return
from qpid.util import connect
from qpid.connection import Connection
from qpid.datatypes import Message, RangedSet
from qpid.queue import Empty


class Producer:
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
        self.session = session

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
        sid = self.sid
        app = dict(consumerid=self.consumerid)
        mp = self.session.message_properties()
        mp.application_headers=app
        if sync:
            mp.reply_to = \
                self.session.reply_to("amq.direct", sid)
        msg = Message(mp, content)
        self.session.message_transfer(destination='amq.match', message=msg)
        if sync:
            return self._getreply()
        else:
            return None

    def _getreply(self):
        """
        Read the reply from our reply queue.
        @return: The json unencoded reply.  Or, (None) on timeout.
        @rtype: any
        """
        try:
            message = self.queue.get(timeout=90)
            self.session.message_accept(RangedSet(message.id))
            reply = Return(message.body)
            if reply.succeeded():
                return reply.retval
            else:
                raise Exception, reply.exval
        except Empty:
            # TODO: something better for timeouts.
            pass
