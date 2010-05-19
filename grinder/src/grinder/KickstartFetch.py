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
LOG = logging.getLogger("grinder.KickstartFetch")



class KickstartFetch(BaseFetch):

    def __init__(self, systemId, baseURL):
        BaseFetch.__init__(self)
        self.baseURL = baseURL
        self.systemId = systemId
        self.rhnComm = RHNComm(baseURL, self.systemId)

    def login(self, refresh=False):
        return self.rhnComm.login(refresh)
    
    def getFetchURL(self, channelLabel, ksLabel, ksFilePath):
        return self.baseURL + "/SAT/$RHN/" + channelLabel + "/getKickstartFile/" + ksLabel + "/" + ksFilePath;

    def fetchItem(self, itemInfo):
        authMap = self.login()

        fileName = itemInfo['relative-path']
        itemSize = itemInfo['size']
        md5sum = itemInfo['md5sum']
        hashType = itemInfo['hashtype']
        ksLabel = itemInfo['ksLabel']
        channelLabel = itemInfo['channelLabel']
        savePath = itemInfo['savePath']
        fetchURL = self.getFetchURL(channelLabel, ksLabel, fileName)
        status = self.fetch(fileName, fetchURL, itemSize, hashType, md5sum, savePath, headers=authMap)
        if status == BaseFetch.STATUS_UNAUTHORIZED:
            LOG.warn("Unauthorized request from fetch().  Will attempt to update authentication credentials and retry")
            authMap = self.login(refresh=True)
            return self.fetch(fileName, fetchURL, itemSize, md5sum, savePath, headers=authMap)
        return status

if __name__ == "__main__":
    import grinder
    grinder.setupLogging(False)

    systemId = open("/etc/sysconfig/rhn/systemid").read()
    baseURL = "http://satellite.rhn.redhat.com"
    channelLabel = "rhel-i386-server-5"
    ksLabel = "ks-rhel-i386-server-5"
    savePath = "./test123"
    kf = KickstartFetch(systemId, baseURL)
    item = {}
    item['relative-path'] = "GPL"
    item['size'] = "18416"
    item['md5sum'] = "6ebd41aa30b178eacb885447b1682e2d"
    item["ksLabel"] = ksLabel
    item["channelLabel"] = channelLabel
    item["savePath"] = savePath
    item["hashtype"] = "md5"
    status = kf.fetchItem(item)
    assert status in [BaseFetch.STATUS_NOOP, BaseFetch.STATUS_DOWNLOADED]
    print "Kickstart fetch of %s has status %s" % (item['relative-path'], status)
    badItem = {}
    badItem['relative-path'] = "EULA"
    badItem['size'] = "8446"
    badItem['md5sum'] = "4cb33358ca64e87f7650525BADbebd67" #intentional bad md5sum
    badItem['hashtype'] = "md5"
    badItem["ksLabel"] = ksLabel
    badItem["channelLabel"] = channelLabel
    badItem["savePath"] = savePath
    status = kf.fetchItem(badItem)
    assert status == BaseFetch.STATUS_MD5_MISSMATCH
    print "Test of bad md5sum passed"
    badItem = {}
    badItem['relative-path'] = "ClusterStorage/repodata/primary.xml.gz"
    badItem['size'] = "123456" #intentional bad size
    badItem['md5sum'] = "66ab1dd4e02e4e0f8655d3ee2489c18a"
    badItem['hashtype'] = "md5"
    badItem["ksLabel"] = ksLabel
    badItem["channelLabel"] = channelLabel
    badItem["savePath"] = savePath
    status = kf.fetchItem(badItem)
    assert status == BaseFetch.STATUS_SIZE_MISSMATCH
    print "Test of bad size passed"
    print "All tests passed"


