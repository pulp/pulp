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
Provides decorator classes & funcitons.
"""

class Remote:
    """
    @cvar classes: A list of remoted classes.
    @cvar aliases: A list of class aliases.
    @cvar methods: A list of remoted methods.
    """
    classes = []
    aliases = {}
    methods = []


def remote(cls):
    """
    Decorator used to register remotable classes.
    @param cls: A class to register.
    @type cls: python class.
    """
    Remote.classes.append(cls)
    return cls

def alias(name=[]):
    """
    @param name: The aliased name.
    @type name: (str|[str,])
    """
    def decorator(cls):
        """
        Decorator used to register remote class synonyms.
        @param cls: A class to register.
        @type cls: python class.
        """
        if isinstance(name, (list,tuple)):
            aliases = name
        else:
            aliases = (name,)
        for alias in aliases:
            Remote.aliases[alias] = cls
        return cls
    return decorator

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
    @type im: instancemethod
    @return: True if exposed via @remotemethod decorator.
    @rtype: bool
    """
    return im.im_func in Remote.methods
