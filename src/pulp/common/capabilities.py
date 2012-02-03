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


class Capabilities:
    """
    Represents general capabilities.
    """

    def __init__(self, definitions, capabilities={}):
        """
        @param definitions: The capabilities definitions:
            {<name>:(<type>,<default>)}
        @type definitions: dict
        @param capabilities: A capabilities dictonary.
        @type capabilities: dict
        """
        self.definitions = definitions
        self.capabilities = {}
        self.update(**capabilities)

    def update(self, **capabilities):
        """
        Update (set) capabilities
        @keyword capabilities: Capabilities to be updated.
        @return: self
        """
        for k,v in capabilities.items():
            capibility = self.definitions[k]
            if isinstance(v, capibility[0]):
                self.capabilities[k] = v
            else:
                raise ValueError('k must be: %s' % capibility[0])
        return self

    def names(self):
        """
        Sorted list of capability names.
        @return:  A list of names.
        @rtype: list
        """
        return sorted(self.definitions.keys())

    def __getattr__(self, name):
        def fn(v=None):
            if v is None:
                return self[name]
            else:
                self.update(**{name:v})
        return fn

    def __getitem__(self, name):
        capibility = self.definitions.get(name)
        if capibility is None:
            raise AttributeError()
        return self.capabilities.get(name, capibility[1])

    def __iter__(self):
        return iter(self.capabilities.items())

    def __str__(self):
        return str(self.capabilities)

    def __repr__(self):
        return repr(self.capabilities)


class AgentCapabilities(Capabilities):
    """
    Represents agent capabilities.
      bind - agent supports bind/unbind API.
      heartbeat - agent supports sending heartbeat.
    """

    def __init__(self, capabilities={}):
        """
        @param capabilities: A capabilities dictonary.
        @type capabilities: dict
        """
        DEFINITIONS = {
            'bind' : (bool, False),
            'heartbeat' : (bool, False),
        }
        Capabilities.__init__(self, DEFINITIONS, capabilities)

    @classmethod
    def default(cls):
        """
        The default agent capabilities.
        @return: The default capabilities
        @rtype: L{AgentCapabilities}
        """
        d = {
             'bind' : True,
             'heartbeat' : True,
        }
        return AgentCapabilities(d)
