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
Contains stub classes.
Proxies (stubs) are the I{local} representation of I{remote}
classes on which we invoke methods.
"""

from pmf import *
from pmf.dispatcher import Request
from pmf.window import Window


class Method:
    """
    A dynamic method object used to wrap the RMI call.
    @ivar classname: The target class name.
    @type classname: str
    @ivar name: The target method name.
    @type name: str
    @ivar stub: The stub object used to send the AMQP message.
    @type stub: L{Stub}
    """

    def __init__(self, classname, name, stub):
        """
        @param classname: The target class name.
        @type classname: str
        @param name: The target method name.
        @type name: str
        @param stub: The stub object used to send the AMQP message.
        @type stub: L{Stub}
        """
        self.classname = classname
        self.name = name
        self.stub = stub

    def __call__(self, *args, **kws):
        """
        Invoke the method .
        @param args: The args.
        @type args: list
        @param kws: The I{keyword} arguments.
        @type kws: dict
        """
        opts = Options()
        for k,v in kws.items():
            if k in ('window', 'any',):
                opts[k] = v
                del kws[k]
        request = Request(
            classname=self.classname,
            method=self.name,
            args=args,
            kws=kws)
        return self.stub._send(request, opts)


class Stub:
    """
    The stub class for remote objects.
    @ivar __pid: The peer ID.
    @type __pid: str
    @ivar __options: Stub options.
    @type __options: dict.
    """

    def __init__(self, pid, options):
        """
        @param pid: The peer ID.
        @type pid: str
        @param options: Stub options.
        @type options: dict
        """
        self.__pid = pid
        self.__options = options

    def _send(self, request, options):
        """
        Send the request using the configured request method.
        @param request: An RMI request.
        @type request: str
        """
        opts = Options(self.__options)
        opts.update(options)
        method = self.__options.method
        if isinstance(self.__pid, (list,tuple)):
            return method.broadcast(
                        self.__pid,
                        request,
                        window=opts.window,
                        any=opts.any)
        else:
            return method.send(
                        self.__pid,
                        request,
                        window=opts.window,
                        any=opts.any)

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
