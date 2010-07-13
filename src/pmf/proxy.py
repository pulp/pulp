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
Contains proxy classes.
Proxies (stubs) are the I{local} representation of I{remote}
classes on which we invoke methods.
"""

from pmf.dispatcher import Request
from pmf.window import Window


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
        Invoke the method .
        @param args: The args.
        @type args: list
        @param kws: The I{keyword} arguments.
        @type kws: dict
        """
        req = Request(
            classname=self.classname,
            method=self.name,
            args=args,
            kws=kws)
        return self.proxy._send(req)


class Proxy:
    """
    The proxy (stub) base class for remote objects.
    @ivar __pid: The peer queue ID.
    @ivar __pid: str
    @ivar __reqmethod: An AMQP message producer.
    @type __reqmethod: L{pmf.policy.RequestMethod}
    @ivar __window: An valid window.
    @type __window: L{Window}
    @ivar __any: Any user defined data.
    @type __any: object
    """

    def __init__(self, peer, reqmethod):
        """
        @ivar peer: The peer consumer ID.
        @ivar peer: str
        @param reqmethod: An AMQP message producer.
        @type reqmethod: L{pmf.policy.RequestMethod}
        """
        self.__pid = peer
        self.__reqmethod = reqmethod
        self.__window = Window()
        self.__any = None

    def _send(self, request):
        """
        Send the request using the configured request method.
        @param request: An RMI request.
        @type request: str
        """
        any = self.__any
        window = self.__window
        if isinstance(self.__pid, (list,tuple)):
            return self.__reqmethod.broadcast(
                        self.__pid,
                        request,
                        window=self.__window,
                        any=self.__any)
        else:
            return self.__reqmethod.send(
                        self.__pid,
                        request,
                        window=self.__window)

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
