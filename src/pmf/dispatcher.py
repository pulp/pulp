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

from pmf.envelope import Envelope
from pmf.decorators import mayinvoke


class ClassNotFound(Exception):
    """
    Target class not found.
    """

    def __init__(self, classname):
        Exception.__init__(self, classname)


class MethodNotFound(Exception):
    """
    Target method not found.
    """

    def __init__(self, classname, method):
        message = 'method %s.%s(), not found' % (classname, method)
        Exception.__init__(self, message)


class NotPermitted(Exception):
    """
    Permission denied or not visible.
    """

    def __init__(self, classname, method):
        message = 'method %s.%s(), not permitted' % (classname, method)
        Exception.__init__(self, message)


class Return(Envelope):
    """
    Return envelope.
    """

    @classmethod
    def succeed(cls, x):
        """
        Return successful
        @param x: The returned value.
        @type x: any
        @return: A return envelope.
        @rtype: L{Return}
        """
        return Return(retval=x)

    @classmethod
    def exception(cls, x):
        """
        Return raised exception.
        @param x: The raised exception.
        @type x: any
        @return: A return envelope.
        @rtype: L{Return}
        """
        return Return(exval=repr(x))

    def succeeded(self):
        """
        Test whether the return indicates success.
        @return: True when indicates success.
        @rtype: bool
        """
        return ( 'retval' in self )

    def failed(self):
        """
        Test whether the return indicates failure.
        @return: True when indicates failure.
        @rtype: bool
        """
        return ( not self.succeeded() )


class Request(Envelope):
    """
    An RMI request envelope.
    """
    pass


class RMI(object):
    """
    The RMI object performs the invocation.
    @ivar request: The request envelope.
    @type request: L{Request}
    @ivar catalog: A dict of class mappings.
    @type catalog: dict
    """

    def __init__(self, request, catalog):
        """
        @param request: The request envelope.
        @type request: L{Request}
        @param catalog: A dict of class mappings.
        @type catalog: dict
        """
        self.request = request
        self.catalog = catalog

    def resolve(self):
        """
        Resolve the class/method in the request.
        @return: A tuple (inst, method)
        @rtype: tuple
        """
        inst = self.getclass()
        method = self.getmethod(inst)
        return (inst, method)

    def getclass(self):
        """
        Get an instance of the class specified in
        the request using the catalog.
        @return: An instance of the class.
        @rtype: object
        """
        key = self.request.classname
        inst = self.catalog.get(key, None)
        if inst is None:
            raise ClassNotFound(key)
        return inst()

    def getmethod(self, inst):
        """
        Get method of the class specified in the request.
        Ensures that remote invocation is permitted.
        @return: The requested method.
        @rtype: instancemethod
        """
        cn, fn = \
            (self.request.classname,
             self.request.method)
        if hasattr(inst, fn):
            method = getattr(inst, fn)
            if not mayinvoke(method):
                raise NotPermitted(cn, fn)
            return method
        else:
            raise MethodNotFound(cn, fn)

    def __call__(self):
        """
        Invoke the method.
        @return: The invocation result.
        @rtype: L{Return}
        """
        args, keywords = \
            (self.request.args,
             self.request.kws)
        try:
            inst, method = self.resolve()
            retval = method(*args, **keywords)
            return Return.succeed(retval)
        except Exception, dx:
            return Return.exception(dx)

    def __str__(self):
        return str(self.request)

    def __repr__(self):
        return str(self)


class Dispatcher:
    """
    The remote invocation dispatcher.
    @ivar classes: The (catalog) of target classes.
    @type classes: list
    """

    def __init__(self):
        """
        """
        self.classes = {}

    def dispatch(self, content):
        """
        Dispatch the requested RMI.
        @param content: A json encoded request.
        @type content: str
        @return: The json encoded result.
        @rtype: str
        """
        request = Request()
        request.load(content)
        rmi = RMI(request, self.classes)
        result = rmi()
        return result.dump()

    def register(self, *classes):
        """
        Register classes exposed as RMI targets.
        @param classes: A list of classes
        @type classes: [cls,..]
        @return self
        @rtype: L{Dispatcher}
        """
        for cls in classes:
            self.classes[cls.__name__] = cls
        return self
