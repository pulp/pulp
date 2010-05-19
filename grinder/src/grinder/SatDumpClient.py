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
import os
from rhn_api import RhnApi
import rpmUtils
import logging

from rhn_transport import RHNTransport

LOG = logging.getLogger("grinder.SatDumpClient")
class SatDumpClient(object):
    def __init__(self, url, verbose=False, transport=None):
        self.baseURL = url
        if not transport:
            transport = RHNTransport()
            transport.addProperty("X-RHN-Satellite-XML-Dump-Version", "3.4")
        self.transport = transport
        self.client = RhnApi(self.baseURL + "/SAT-DUMP/", 
                verbose=verbose, transport=self.transport)

    def getChannelFamilies(self, systemId):
        retVal = {}
        dom = self.client.dump.channel_families(systemId)
        # rhn-channel-family label=""  channel_labels="" id =""
        rhnChannelFamilies = dom.getElementsByTagName("rhn-channel-family")
        for channelFam in rhnChannelFamilies:
            label = channelFam.getAttribute("label")
            tmp = channelFam.getAttribute("channel-labels")
            channelFamChannelLabels = tmp.split(" ")
            rhn_id = channelFam.getAttribute("id")
            val = {"label":label, "channel_labels":channelFamChannelLabels, "id":rhn_id}
            retVal[label] = val
        return retVal

    def getKickstartLabels(self, systemId, channelLabels):
        dom = self.client.dump.channels(systemId, channelLabels)
        #Need to read attribute "kickstartable-trees"
        #Example: kickstartable_trees="ks-rhel-i386-server-5 ks-rhel-i386-server-5-u1 
        #  ks-rhel-i386-server-5-u2 ks-rhel-i386-server-5-u3 ks-rhel-i386-server-5-u4"
        ksTrees = {}
        rhnChannels = dom.getElementsByTagName("rhn-channel")
        for channel in rhnChannels:
            if "kickstartable-trees" in channel.attributes.keys():
                ksTrees[channel.getAttribute("label")] = channel.getAttribute("kickstartable-trees").split()
        return ksTrees
    
    def getKickstartTreeMetadata(self, systemId, ksLabels):
        retVal = {}
        dom = self.client.dump.kickstartable_trees(systemId, ksLabels)
        ksTreeElements = dom.getElementsByTagName("rhn-kickstartable-tree")
        for ksTree in ksTreeElements:
            #Example: <rhn-kickstartable-tree base-path="rhn/kickstart/ks-rhel-x86_64-server-5-u4" 
            #  boot-image="ks-rhel-x86_64-server-5-u4" channel="rhel-x86_64-server-5" 
            #  install-type-label="rhel_5" install-type-name="Red Hat Enterprise Linux 5" 
            #  kstree-type-label="rhn-managed" kstree-type-name="RHN managed kickstart tree" 
            #  label="ks-rhel-x86_64-server-5-u4" 
            #  last-modified="1253669992">
            ksLabel = ksTree.getAttribute("label")
            retVal[ksLabel] = {}
            retVal[ksLabel]["base-path"] = ksTree.getAttribute("base-path") 
            retVal[ksLabel]["last-modified"] = ksTree.getAttribute("last-modified") 
            retVal[ksLabel]["channel"] = ksTree.getAttribute("channel")
            retVal[ksLabel]["files"] = []
            ksFilesElements = ksTree.getElementsByTagName("rhn-kickstart-files")
            for ksFile in ksFilesElements:
                files = ksFile.getElementsByTagName("rhn-kickstart-file")
                for f in files:
                    # <rhn-kickstart-files>
                    #  <rhn-kickstart-file file-size="112" last-modified="1250668122" 
                    #     md5sum="1bbc90ffcc96b5c6edea23876ad80f66" relative-path=".discinfo"/>
                    fileInfo = {}
                    fileInfo["hashtype"] = "md5"
                    for key in ["file-size", "last-modified", "relative-path", "md5sum"]:
                        fileInfo[key] = f.getAttribute(key)
                    retVal[ksLabel]["files"].append(fileInfo)
        return retVal

    def getProductNames(self, systemId):
        retVal = {}
        dom = self.client.dump.product_names(systemId)
        rhnProductNames = dom.getElementsByTagName("rhn-product-name")
        for productName in rhnProductNames:
            name = productName.getAttribute("name")
            label = productName.getAttribute("label")
            val = {"label":label, "name":name}
            retVal[label] = val
        return retVal

    def getChannelPackages(self, systemId, channelLabel):
        dom = self.client.dump.channels(systemId, [channelLabel])
        rhn_channel = dom.getElementsByTagName("rhn-channel")[0]
        packages = rhn_channel.getAttribute("packages")
        return packages.split(" ")
  
    def getShortPackageInfo(self, systemId, listOfPackages, filterLatest=True):
        """
        Input:
         systemId
         listOfPackages -   list of rhn-package-ids
         filterLatest   -   optional, default value is True.  This will limit 
                              returned packages to only latest in channel
        Returns:
          dict of short package info
            key is the name.arch if filterLatest=True, or NEVRA if filterLatest=False
        """
        dom = self.client.dump.packages_short(systemId, listOfPackages)
        #Example of data
        # <rhn-package-short name="perl-Sys-Virt" package-size="137602" 
        #  md5sum="dfd888260a1618e0a2cb6b3b5b1feff9" 
        #  package-arch="i386" last-modified="1251397645" epoch="" version="0.2.0" release="4.el5" 
        #  id="rhn-package-492050"/>
        #
        rhn_package_shorts = dom.getElementsByTagName("rhn-package-short")
        packages = {}
        for pkgShort in rhn_package_shorts:
            pkgName, nevra, info = self.convertPkgShortToDict(pkgShort)
            if filterLatest:
                # only fetching latest packages, so dict key of 
                # 'name'.'arch' is what we want to be unique
                pkgKey = pkgName+"." + info["arch"]
                if not packages.has_key(pkgKey):
                    LOG.debug("Adding package %s to queue", nevra)
                    packages[pkgKey] = info
                else:
                    #package already in our dict, so check to keep only latest nevra
                    potentialOld = packages.get(pkgKey)
                    LOG.debug("A version for %s already exists, will need to compare to determine latest" \
                        % (pkgKey))
                    LOG.debug("Existing: %s, new addition: %s" % (potentialOld["nevra"], nevra))
                    if self.isNewerEVR(info, potentialOld):
                        LOG.debug("Removing %s and adding %s" % (potentialOld["nevra"], nevra))
                        packages[pkgKey] = info
            else:
                # Fetching all packages, not just latest.  
                # dict key needs to contain full nevra to be unique now
                packages[nevra] = info
        return packages

    def isNewerEVR(self, pkgOne, pkgTwo):
        # Only check for packages of same arch
        if pkgOne["arch"] != pkgTwo["arch"]:
            return False
        e1 = pkgOne["epoch"]
        v1 = pkgOne["version"]
        r1 = pkgOne["release"]

        e2 = pkgTwo["epoch"]
        v2 = pkgTwo["version"]
        r2 = pkgTwo["release"]

        if rpmUtils.miscutils.compareEVR((e1,v1,r1), (e2,v2,r2)) == 1:
            return True
        return False

    def formNEVRA(self, info):
        nevra = info["name"]
        epoch = info["epoch"]
        if epoch:
            nevra += "-" + epoch + ":"
        nevra += "-" + info["version"] + "-" + info["release"]
        arch = info["arch"]
        if arch:
            nevra += "." + arch
        nevra += ".rpm"
        return nevra

    def formFetchName(self, info):
        release_epoch = info["release"] + ":" + info["epoch"]
        return info["name"] + "-" + info["version"] + "-" + release_epoch + "." + info["arch"] + ".rpm"

    def formFileName(self, info):
        return info["name"] + "-" + info["version"] + "-" + info["release"] + "." + info["arch"] + ".rpm"

    def convertPkgShortToDict(self, pkgShort):
        info = {}
        name = pkgShort.getAttribute("name")
        info["name"] = name
        info["package_size"] = pkgShort.getAttribute("package-size")
        info["hashtype"] = "md5"
        info["md5sum"] = pkgShort.getAttribute("md5sum")
        info["arch"] = pkgShort.getAttribute("package-arch")
        info["last_modified"] = pkgShort.getAttribute("last-modified")
        info["epoch"] = pkgShort.getAttribute("epoch")
        info["version"] = pkgShort.getAttribute("version")
        info["release"] = pkgShort.getAttribute("release")
        info["id"] = pkgShort.getAttribute("id")
        info["fetch_name"] = self.formFetchName(info)
        nevra = self.formNEVRA(info)
        info["nevra"] = nevra
        info["filename"] = self.formFileName(info)
        return name, nevra, info




if __name__ == "__main__":
    sysIdPath = "/etc/sysconfig/rhn/systemid"
    
    logging.basicConfig(filename="./SatDumpClient-debug.log", level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M', filemode='w')

    if not os.path.isfile(sysIdPath):
        print "Can't find file: %s" % (sysIdPath)
        sys.exit(1)
    sysId = open(sysIdPath, "r").read()
    url = "http://satellite.rhn.redhat.com"
    satDump = SatDumpClient(url)
    productNames = satDump.getProductNames(sysId)
    print "\nProduct Names:\n\t %s\n" % (productNames)
    
    channelFamilies = satDump.getChannelFamilies(sysId)
    print "\nChannel Families:\n\t %s\n" % (channelFamilies)

    channelPkgs = []
    if len(channelFamilies) > 0:
        lbls = channelFamilies.values()[0].get("channel_labels")
        if len(lbls):
            label = lbls[0]
            channelPkgs = satDump.getChannelPackages(sysId, label)
            print "\nChannel Packages for <%s>:\n\t %s\n" % (label, channelPkgs)

    if len(channelPkgs) > 0:
        pkg = channelPkgs[0]
        pkgShort = satDump.getShortPackageInfo(sysId, [pkg])
        print "\nPackage metadata for <%s>:\n\t %s\n" % (pkg, pkgShort)



