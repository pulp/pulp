#!/usr/bin/python
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
from pulp.client.logutil import getLogger
import utils
import rpm
log = getLogger(__name__)

"""
Module for Package profile accumulation
"""

class PackageProfile(object):
    """
    Class for probing package profile info
    @ivar type: type of package content to run lookups on eg: 'rpm','jar','zip' etc.
    @type TYPE: str
    """
    def __init__(self, type='rpm'):
        self.pkgtype = type
        self.pkglist = {}
        
    def getPackageList(self):
        """
        Get I{ordered} pkg hash objects.
        @return: A list of ordered pkg hash objects.
        @rtype: list
        """
        if self.pkgtype == 'rpm':
            return self.__getInstalledRpms()

    def __getInstalledRpms(self):
        """ Accumulates list of installed rpm info """
        ts = rpm.TransactionSet()
        ts.setVSFlags(-1)
        installed = ts.dbMatch()
        self.pkglist = utils.generatePakageProfile(installed)
        return self.pkglist
    
    def _getInstalledJars(self):
        pass
    
    def _getInstalledZips(self):
        pass


if __name__ == '__main__':
    pp = PackageProfile()
    import pprint
    pprint.pprint(pp.getPackageList())
