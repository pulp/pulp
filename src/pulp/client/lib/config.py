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
from iniparse import INIConfig


class Config(INIConfig):
    """
    The pulp client configuration.
    @cvar USER_PATH: The path to an alternate configuration file
        within the user's home.
    @type USER_PATH: str
    @cvar BASE_PATH: The absolute path to the config directory.
    @type BASE_PATH: str
    @cvar FILE: The name of the config file.
    @type FILE: str
    @cvar ALT: The environment variable with a path to an alternate
        configuration file.
    @type ALT: str
    @cvar FILE_PATH: The absolute path of the config file.
    @type FILE_PATH: str
    """

    USER_PATH = "~/.pulp"

    # These variables should be set in subclasses.
    BASE_PATH = ""
    FILE = ""

    # ALT can optionally be set in a subclass, but is not required.
    ALT = ""

    # These variables are set in __init__, but need to be defined as class
    # variables since we inherit from INIConfig.
    FILE_PATH = ""

    def __init__(self):
        """
        Open the configuration.
        Merge (in) alternate configuration file when specified
        by environment variable.
        """

        # This class is meant to be subclassed for specific config
        # implementations.  Each subclass should set the FILE attribute.
        if self.FILE == "" or self.BASE_PATH == "":
            raise NotImplementedError("Base Config Class can not be "
                "instantiated")

        self.FILE_PATH = os.path.join(self.BASE_PATH, self.FILE)

        fp = open(self.FILE_PATH)
        try:
            INIConfig.__init__(self, fp)
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
        return self.__mergeIn(INIConfig(open(path)))

    def __mergeIn(self, other):
        """
        Merge (in) the specified I{other} configuration.
        @param other: The conf to merge in.
        @type other: INIConfig
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
        @type other: INIConfig
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
        @rtype: INIConfig
        """
        fp = open(path)
        try:
            return INIConfig(fp)
        finally:
            fp.close()


    def __altpath(self):
        """
        Get the I{alternate} configuration path.
        Resolution order: ALT, USER_PATH
        @return: The path to the alternate configuration file.
        @rtype: str
        """
        if self.ALT:
            path =  os.environ.get(self.ALT)
            if path:
                return path
        user_path = os.path.join(os.path.expanduser(self.USER_PATH),
            self.FILE)
        if os.path.exists(user_path):
            return user_path
        else:
            None
