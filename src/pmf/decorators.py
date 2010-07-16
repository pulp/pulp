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
Provides decorator functions.
B{remoteclasses} contain the list of registered classes that may
be accessed remotely.
B{remotemethods} contain the list of methods on I{remote} classes
that may be invoked remotely.
"""

class Remote:
    """
    @cvar classes: A list of remoted classes.
    @cvar methods: A list of remoted methods.
    """
    classes = []
    methods = []


def remote(cls):
    """
    Decorator used to register remotable classes.
    @param cls: A class to register.
    @type cls: python class.
    """
    Remote.classes.append(cls)
    return cls

def remotemethod(fn):
    """
    @param fn: A function related to an instancemethod.
    @type fn: function
    Decorator used to register methods that may
    be invoked remotely.
    """
    Remote.methods.append(fn)
    return fn

def mayinvoke(im):
    """
    Get whether the specified instance method (im)
    may be invoked remotely.
    @param im: An instance method.
    @type im: L{instancemethod}
    @return: True if exposed via @remotemethod decorator.
    @rtype: bool
    """
    return im.im_func in Remote.methods


class Stubs:
    """
    Stubs
    @ivar classes: List of subs classes.
    @type classes: list
    """
    stubs = {}


def stub(ns):
    """
    Decorator used to register sub classes.
    @param ns: The stub namespace.
    @type ns: str.
    """
    def decorator(cls):
        Stubs.stubs[ns] = cls
        return cls
    return decorator
