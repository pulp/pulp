#!/usr/bin/env python
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
import logging

from BaseFetch import BaseFetch
from RHNComm import RHNComm
LOG = logging.getLogger("grinder.PackageFetch")


class PackageFetch(BaseFetch):
    
    def __init__(self, systemId, baseURL, channelLabel, savePath):
        BaseFetch.__init__(self)
        self.systemId = systemId
        self.baseURL = baseURL
        self.rhnComm = RHNComm(baseURL, self.systemId)
        self.channelLabel = channelLabel
        self.savePath = savePath

    def login(self, refresh=False):
        """
        Returns authentication headers needed for RHN 'GET' requests.
        auth data is cached, if data needs to be updated, pass in refresh=True
        """
        return self.rhnComm.login(refresh)

    def getFetchURL(self, channelLabel, fetchName):
        return self.baseURL + "/SAT/$RHN/" + channelLabel + "/getPackage/" + fetchName;

    def fetchItem(self, itemInfo):
        authMap = self.login()
        fileName = itemInfo['filename']
        fetchName = itemInfo['fetch_name']
        itemSize = itemInfo['package_size']
        md5sum = itemInfo['md5sum']
        hashType = itemInfo['hashtype']
        fetchURL = self.getFetchURL(self.channelLabel, fetchName)
        status = self.fetch(fileName, fetchURL, itemSize, hashType, md5sum, self.savePath, headers=authMap)
        if status == BaseFetch.STATUS_UNAUTHORIZED:
            LOG.warn("Unauthorized request from fetch().  Will attempt to update authentication credentials and retry")
            authMap = self.login(refresh=True)
            return self.fetch(fileName, fetchURL, itemSize, md5sum, self.savePath, headers=authMap)
        return status

if __name__ == "__main__":
    import GrinderLog
    GrinderLog.setup(True)
    systemId = open("/etc/sysconfig/rhn/systemid").read()
    baseURL = "http://satellite.rhn.redhat.com"
    channelLabel = "rhel-i386-server-vt-5"
    savePath = "./test123"
    pf = PackageFetch(systemId, baseURL, channelLabel, savePath)
    pkg = {}
    pkg['nevra'] = "Virtualization-es-ES-5.2-9.noarch.rpm"
    pkg['fetch_name'] = "Virtualization-es-ES-5.2-9:.noarch.rpm"
    pkg['package_size'] = "1731195"
    pkg['md5sum'] = "91b0f20aeeda88ddae4959797003a173" 
    pkg['hashtype'] = 'md5'
    pkg['filename'] = "Virtualization-es-ES-5.2-9.noarch.rpm"
    status = pf.fetchItem(pkg)
    print "Package fetch status is %s" % (status)

