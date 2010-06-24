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
Provides AMQP message consumer classes.
"""

from pmf import *
from pmf.base import Endpoint
from pmf.envelope import Envelope
from qpid.util import connect
from qpid.connection import Connection
from qpid.datatypes import Message, RangedSet
from qpid.queue import Empty

class Consumer(Endpoint):
    """
    An AMQP consumer.
    @ivar queue: The primary incoming message queue.
    @type queue: L{qpid.Queue}
    @ivar session: An AMQP session.
    @type session: L{qpid.Session}
    """

    def __init__(self, id, host='localhost', port=5672):
        """
        @param host: The fqdn or IP of the QPID broker.
        @type host: str
        @param port: The port of the QPID broker.
        @type port: short
        """
        socket = connect(host, port)
        connection = Connection(sock=socket)
        connection.start()
        sid = getuuid()
        session = connection.session(sid)
        session.queue_declare(queue=id, exclusive=True)
        session.exchange_bind(
            exchange='amq.match',
            queue=id,
            binding_key=id,
            arguments={'x-match':'any','consumerid':id})
        session.message_subscribe(queue=id, destination=id)
        self.queue = session.incoming(id)
        Endpoint.__init__(self, session)

    def start(self, dispatcher):
        """
        Start processing messages on the queue using the
        specified dispatcher.
        @param dispatcher: An RMI dispatcher.
        @type dispatcher: L{pmf.Dispatcher}
        @return: self
        @rtype: L{Consumer}
        """
        self.queue.start()
        while True:
            try:
                message = self.queue.get(timeout=10)
                envelope = Envelope()
                envelope.load(message.body)
                sn = envelope.sn
                content = envelope.payload
                result = dispatcher.dispatch(content)
                self.__respond(envelope, result)
                self.acceptmessage(message.id)
            except Empty:
                pass

    def __respond(self, request, result):
        """
        Respond to request with the specified I{content}.
        A response is send B{only} when a I{replyto} is specified
        in the I{message}.
        @param request: The request envelope.
        @type request: L{Envelope}
        @param result: A reply object.
        @type result: L{pmf.Return}
        """
        replyto = request.replyto
        if not replyto:
            return
        envelope = Envelope(sn=request.sn)
        envelope.payload = result
        dest = replyto[0]
        key = replyto[1]
        dp = self.session.delivery_properties(routing_key=key)
        reply = Message(dp, envelope.dump())
        self.session.message_transfer(destination=dest, message=reply)
        return self
