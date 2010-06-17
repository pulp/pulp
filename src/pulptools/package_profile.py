#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Pradeep Kilambi <pkilambi@redhat.com>
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
from pulptools.logutil import getLogger
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
        
        import rpm
        ts = rpm.TransactionSet()
        ts.setVSFlags(-1)
        installed = ts.dbMatch()
        for h in installed:
            if h['name'] == "gpg-pubkey":
                #dbMatch includes imported gpg keys as well
                # skip these for now as there isnt compelling 
                # reason for server to know this info
                continue
            info = {
                'name'          : h['name'],
                'version'       : h['version'],
                'release'       : h['release'],
                'epoch'         : h['epoch'] or "",
                'arch'          : h['arch'],
                'installtime'   : h['installtime'],
                'group'         : h['Group'] or "",
                'summary'       : h['Summary'],
                'description'   : h['description'],
                'OS'            : h['OS'],
                'Platform'      : h['Platform'],
                'URL'           : h['URL'],
                'Size'          : h['Size'],
                'Vendor'        : h['Vendor'],             
            }
            if not self.pkglist.has_key(h['name']):
                self.pkglist[h['name']] = [info]
            else:
                self.pkglist[h['name']].append(info)

        return self.pkglist
    
    def getRpmName(self, pkg):
        return pkg["name"] + "-" + pkg["version"] + "-" + \
               pkg["release"] + "." + pkg["arch"]
    
    def _getInstalledJars(self):
        pass
    
    def _getInstalledZips(self):
        pass


if __name__ == '__main__':
    pp = PackageProfile()
    import pprint
    pprint.pprint(pp.getPackageList())
