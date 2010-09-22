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

from uuid import uuid4
import simplejson as json

version = '0.1'


def getuuid():
    return str(uuid4())


class Options(dict):
    """
    Container options.
    Options:
      - async : Indicates that requests asynchronous.
          Default = False
      - ctag : The asynchronous correlation tag.
          When specified, it implies all requests are asynchronous.
      - window : The request window.  See I{Window}.
          Default = any time.
      - timeout : The synchronous timeout (seconds).
          Default = 90 seconds.
    """
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__= dict.__delitem__


class Envelope(dict):
    """
    Basic envelope is a json encoded/decoded dictionary
    that provides dot (.) style access.
    """

    __getattr__ = dict.get
    __setattr__= dict.__setitem__
    __delattr__= dict.__delitem__

    def load(self, s):
        """
        Load using a json string.
        @param s: A json encoded string.
        @type s: str
        """
        d = json.loads(s)
        self.update(d)
        return self

    def dump(self):
        """
        Dump to a json string.
        @return: A json encoded string.
        @rtype: str
        """
        d = self
        return json.dumps(d, indent=2)

    def __str__(self):
        return self.dump()


class Destination:
    """
    AMQP destinations (topics & queues)
    """

    def address(self):
        """
        Get the destination I{formal} AMQP address which contains
        properties used to create the destination.
        @return: The destination address.
        @rtype: str
        """
        pass

    def delete(self, session):
        """
        Delete the destination.
        Implemented using a hack becauase python API does not
        directly support removing destinations.
        @param session: An AMQP session.
        @type session: I{qpid.messaging.Session}
        """
        address = '%s;{delete:always}' % repr(self)
        sender = session.sender(address)
        sender.close()

    def __repr__(self):
        return str(self).split(';', 1)[0]


class Topic(Destination):
    """
    Represents and AMQP topic.
    @ivar topic: The name of the topic.
    @type topic: str
    @ivar subject: The subject.
    @type subject: str
    @ivar name: The (optional) subscription name.
        Used for durable subscriptions.
    @type name: str
    """

    def __init__(self, topic, subject=None, name=None):
        """
        @param topic: The name of the topic.
        @type topic: str
        @param subject: The subject.
        @type subject: str
        @param name: The (optional) subscription name.
            Used for durable subscriptions.
        @type name: str
        """
        self.topic = topic
        self.subject = subject
        self.name = name

    def address(self):
        """
        Get the topic I{formal} AMQP address which contains
        properties used to create the topic.
        @return: The topic address.
        @rtype: str
        """
        s = []
        s.append(self.topic)
        if self.subject:
            s.append('/%s' % self.subject)
        s.append(';{')
        s.append('create:always')
        s.append(',node:{type:topic,durable:True}')
        s.append(',link:{durable:True,x-declare:{arguments:{no-local:True}}}')
        s.append('}')
        return ''.join(s)

    def queuedAddress(self):
        """
        Get the topic I{durable} AMQP address which contains
        properties used to create the topic.
        @return: The topic address.
        @rtype: str
        """
        s = []
        s.append(self.name)
        s.append(';{')
        s.append('create:always')
        s.append(',node:{type:topic,durable:True}')
        s.append(',link:{durable:True')
        s.append(',x-bindings:[')
        s.append('{exchange:%s' % self.topic)
        if self.subject:
            s.append(',key:%s' % self.subject)
        s.append('}]')
        s.append('}}')
        return ''.join(s)

    def __str__(self):
        if self.name:
            return self.queuedAddress()
        else:
            return self.address()


class Queue(Destination):
    """
    Represents and AMQP queue.
    @ivar name: The name of the queue.
    @type name: str
    @ivar durable: The durable flag.
    @type durable: str
    """

    def __init__(self, name, durable=True):
        """
        @param name: The name of the queue.
        @type name: str
        @param durable: The durable flag.
        @type durable: str
        """
        self.name = name
        self.durable = durable

    def address(self):
        """
        Get the queue I{formal} AMQP address which contains
        properties used to create the queue.
        @return: The queue address.
        @rtype: str
        """
        s = []
        s.append(self.name)
        s.append(';{')
        s.append('create:always')
        s.append(',node:{type:queue,durable:True}')
        s.append(',link:{durable:True}')
        s.append('}')
        return ''.join(s)

    def tmpAddress(self):
        """
        Get the queue AMQP address which contains
        properties used to create a temporary queue.
        @return: The queue address.
        @rtype: str
        """
        s = []
        s.append(self.name)
        s.append(';{')
        s.append('create:always,delete:receiver')
        s.append(',node:{type:queue}')
        s.append(',link:{durable:True}')
        s.append('}')
        return ''.join(s)

    def __str__(self):
        if self.durable:
            return self.address()
        else:
            return self.tmpAddress()
