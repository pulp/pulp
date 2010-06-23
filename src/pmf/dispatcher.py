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

import simplejson as json
from pmf.decorators import mayinvoke


class ClassNotFound(Exception):

    def __init__(self, classname):
        Exception.__init__(self, classname)


class MethodNotFound(Exception):

    def __init__(self, classname, method):
        message = 'method %s.%s(), not found' % (classname, method)
        Exception.__init__(self, message)


class NotPermitted(Exception):

    def __init__(self, classname, method):
        message = 'method %s.%s(), not permitted' % (classname, method)
        Exception.__init__(self, message)


class Return:

    @classmethod
    def succeed(cls, x):
        d = dict(retval=x)
        return json.dumps(d, indent=2)

    @classmethod
    def exception(cls, x):
        d = dict(exval=repr(x))
        return json.dumps(d, indent=2)

    def __init__(self, v):
        self.__dict__ = json.loads(v)

    def succeeded(self):
        return hasattr(self, 'retval')

    def failed(self):
        return ( not self.succeeded() )


class RMI(object):

    @classmethod
    def encode(cls, classname, method, args, kws):
        d = dict(
            classname=classname,
            method=method,
            args=args,
            kws=kws)
        return json.dumps(d, indent=2)

    def __init__(self, content, catalog):
        self.catalog = catalog
        self.__dict__.update(json.loads(content))

    def resolve(self):
        inst = self.resolveclass()
        method = self.resolvemethod(inst)
        return (inst, method)

    def resolveclass(self):
        inst = self.catalog.find(self.classname)
        if inst is None:
            raise ClassNotFound(self.classname)
        return inst()

    def resolvemethod(self, inst):
        if hasattr(inst, self.method):
            method = getattr(inst, self.method)
            if not mayinvoke(method):
                raise NotPermitted(self.classname, self.method)
            return method
        else:
            raise MethodNotFound(self.classname, self.method)

    def __call__(self):
        try:
            inst, method = self.resolve()
            retval = method(*self.args, **self.kws)
            return Return.succeed(retval)
        except Exception, dx:
            return Return.exception(dx)

    def __str__(self):
        return '%s.%s(%s,%s)' %\
            (self.classname,
             self.method,
             str(self.args),
             str(self.kws))

    def __repr__(self):
        return str(self)


class Dispatcher:

    def __init__(self):
        self.classes = {}

    def dispatch(self, content):
        rmi = RMI(content, self)
        return rmi()

    def register(self, *classes):
        for cls in classes:
            self.classes[cls.__name__] = cls

    def find(self, classname):
        return self.classes.get(classname)
