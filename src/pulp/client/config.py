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


import os
from iniparse import INIConfig as Base


class Config(Base):
    """
    The pulp client configuration.
    @cvar PATH: The absolute path to the config directory.
    @type PATH: str
    @cvar ALTVAR: The environment variable with a path to an alternate
        configuration file.  This file is merged.
    @type ALTVAR: str
    """

    PATH = '/etc/pulp/client.conf'
    ALTVAR = 'PULP_CLIENT_ALTCONF'

    def __init__(self):
        """
        Open the configuration.
        Merge alternate configuration file when specified
        by environment variable.
        """
        fp = open(self.PATH)
        try:
            Base.__init__(self, fp)
            alt = os.environ.get(self.ALTVAR)
            if alt:
                self.__merge(alt)
        finally:
            fp.close()

    def write(self):
        """
        Write the configuration.
        """
        fp = open(self.PATH, 'w')
        try:
            fp.write(str(self))
        finally:
            fp.close()

    def __merge(self, path):
        """
        Merge the configuration file at the specified path.
        @param path: The path to a configuration file.
        @type path: str
        @return: self
        @rtype: L{Config}
        """
        fp = open(path)
        try:
            other = Base(fp)
        finally:
            fp.close()
        for section in other:
            sA = self[section]
            sB = other[section]
            for key in sB:
                value = sB[key]
                setattr(sA, key, value)
        return self
