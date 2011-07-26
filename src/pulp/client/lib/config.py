#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#


import os
from iniparse import INIConfig as Base


class Config(Base):
    """
    The pulp client configuration.
    @cvar PATH: The absolute path to the config directory.
    @type PATH: str
    @cvar USER: The path to an alternate configuration file
        within the user's home.
    @type USER: str
    @cvar ALT: The environment variable with a path to an alternate
        configuration file.
    @type ALT: str
    """

    # FILE should be overridden in the base class.
    FILE = ''
    PATH = '/etc/pulp'
    FILE_PATH = ''
    USER = ''
    ALT = 'PULP_CLIENT_OVERRIDE'

    def __init__(self):
        """
        Open the configuration.
        Merge (in) alternate configuration file when specified
        by environment variable.
        """

        # This class is meant to be subclassed for specific config
        # implementations.  Each subclass should set the FILE attribute.
        if self.FILE == '':
            raise NotImplementedError("Base Config Class can not be "
                "instantiated")

        self.FILE_PATH = os.path.join(self.PATH, self.FILE)
        self.USER = os.path.join('~/.pulp', self.FILE)

        fp = open(self.FILE_PATH)
        try:
            Base.__init__(self, fp)
            altpath = self.__altpath()
            if altpath:
                alt = self.__read(altpath)
                self.__mergeIn(alt)
        finally:
            fp.close()

    def write(self):
        """
        Write the configuration.
        """
        altpath = self.__altpath()
        if altpath:
            alt = self.__read(altpath)
            self.__mergeOut(alt)
            path = altpath
            s = str(alt)
        else:
            path = self.FILE_PATH
            s = str(self)
        fp = open(path, 'w')
        try:
            fp.write(s)
        finally:
            fp.close()

    def merge(self, path):
        return self.__mergeIn(Base(open(path)))

    def __mergeIn(self, other):
        """
        Merge (in) the specified I{other} configuration.
        @param other: The conf to merge in.
        @type other: Base
        @return: self
        @rtype: L{Config}
        """
        for section in other:
            if section not in self:
                for option in other[section]:
                    self[section][option] = other[section][option]
            else:
                sA = self[section]
                sB = other[section]
                for key in sB:
                    value = sB[key]
                    setattr(sA, key, value)
        return self

    def __mergeOut(self, other):
        """
        Merge (out) to the specified I{other} configuration.
        @param other: The conf to merge out.
        @type other: Base
        @return: self
        @rtype: L{Config}
        """
        for section in other:
            if section not in self:
                continue
            sA = self[section]
            sB = other[section]
            for key in sB:
                value = sA[key]
                setattr(sB, key, value)
        return self

    def __read(self, path):
        """
        Read the configuration at the specified path.
        @param path: The fully qualified path.
        @type path: str
        @return: The configuration object.
        @rtype: Base
        """
        fp = open(path)
        try:
            return Base(fp)
        finally:
            fp.close()


    def __altpath(self):
        """
        Get the I{alternate} configuration path.
        Resolution order: ALT, USER
        @return: The path to the alternate configuration file.
        @rtype: str
        """
        path =  os.environ.get(self.ALT)
        if path:
            return path
        path = os.path.expanduser(self.USER)
        if os.path.exists(path):
            return path
        else:
            None
