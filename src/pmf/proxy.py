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
Contains proxy classes.
Proxies (stubs) are the I{local} representation of I{remote}
classes on which we invoke methods.
"""

from pmf.producer import Producer
from pmf.dispatcher import RMI


class Method:
    """
    A dynamic method object used to wrap the RMI call.
    @ivar classname: The target class name.
    @type classname: str
    @ivar name: The target method name.
    @type name: str
    @ivar proxy: The proxy object used to send the AMQP message.
    @type proxy: L{Proxy}
    """

    def __init__(self, classname, name, proxy):
        """
        @param classname: The target class name.
        @type classname: str
        @param name: The target method name.
        @type name: str
        @param proxy: The proxy object used to send the AMQP message.
        @type proxy: L{Proxy}
        """
        self.classname = classname
        self.name = name
        self.proxy = proxy

    def __call__(self, *args, **kws):
        """
        Invoke the method.
        Strip the "__sync" keyword then send.
        @param args: The args.
        @type args: list
        @param kws: The I{keyword} arguments.
        @type kws: dict
        """
        synckey = '__sync'
        sync = True
        if synckey in kws:
            sync = kws[synckey]
            del kws[synckey]
        content = RMI.encode(
            self.classname,
            self.name,
            args,
            kws)
        return self.proxy._send(content, sync)


class Proxy:
    """
    The proxy (stub) base class for remote objects.
    @ivar producer: An AMQP message producer.
    @type producer: L{pmf.Producer}
    """

    def __init__(self, producer):
        """
        @param producer: An AMQP message producer.
        @type producer: L{pmf.Producer}
        """
        self.__producer = producer

    def _send(self, content, sync):
        """
        Send the message using the configured producer.
        @param content: json encoded RMI request.
        @type content: str
        @param sync: The synchronous/asynchronous flag.
        @type sync: bool
        """
        return self.__producer.send(content, sync)

    def __getattr__(self, name):
        """
        Python vodo.
        Get a I{Method} object for any requested attribte.
        @param name: The attribute name.
        @type name: str
        @return: A method object.
        @rtype: L{Method}
        """
        cn = self.__class__.__name__
        return Method(cn, name, self)
