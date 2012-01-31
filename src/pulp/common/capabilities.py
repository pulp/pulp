# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.


class AgentCapabilities:
    """
    Represents agent capabilities.
    @cvar BIND: Supports bind/unbind API.
    @type BIND: bool
    @cvar HEARTBEAT: Supports sending heartbeats.
    @type HEARTBEAT: bool
    @ivar capabilities: The capabilities dictionary.
    @type capabilities: dict
    """

    # properties
    BIND = 'bind'
    HEARTBEAT = 'heartbeat'

    # default (pulp)
    DEFAULT = {
        BIND : True,
        HEARTBEAT : True,
    }

    def __init__(self, capabilities={}):
        """
        @param capabilities: A capabilities dictonary.
        @type capabilities: dict
        """
        self.capabilities = dict(capabilities)

    def bind(self, flag=None):
        """
        Get/Set (bind) capability.
        Indicates that the agent implements the bind/unbind API.
        @param flag: (optional) New value when specified.
        @type flag: bool
        @return: True if (bind) capability is SET.
        @rtype: bool
        """
        if flag is None:
            return self.capabilities.get(self.BIND, False)
        else:
            self.capabilities[self.BIND] = bool(flag)
            return flag

    def heartbeat(self, flag=None):
        """
        Get/Set (heartbeat) capability.
        Indicates that the agent sends heartbeats.
        @param flag: (optional) New value when specified.
        @type flag: bool
        @return: True if (heartbeat) capability is SET.
        @rtype: bool
        """
        if flag is None:
            return self.capabilities.get(self.BIND, False)
        else:
            self.capabilities[self.HEARTBEAT] = bool(flag)
            return flag

    def __str__(self):
        return str(self.capabilities)

    def __repr__(self):
        return repr(self.capabilities)
