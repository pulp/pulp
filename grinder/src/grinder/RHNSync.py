#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Mike McCune, John Matthews
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
import sys
import pdb
import glob
import httplib
import urlparse
import time
import commands
import rpm
import rpmUtils
import rpmUtils.miscutils
try:
    import hashlib as md5
except:
    import md5
import logging
import signal
from ParallelFetch import ParallelFetch
from KickstartFetch import KickstartFetch

from xmlrpclib import Fault

from rhn_api import RhnApi
from rhn_api import getRhnApi
from rhn_transport import RHNTransport
from ParallelFetch import ParallelFetch
from PackageFetch import PackageFetch
from GrinderExceptions import *
from SatDumpClient import SatDumpClient
from RHNComm import RHNComm
from BaseSync import BaseSync

LOG = logging.getLogger("grinder.RHNSync")

class RHNSync(BaseSync):
    def __init__(self):
        BaseSync.__init__(self)
        self.baseURL = "http://satellite.rhn.redhat.com"
        try:
            certFile = "/etc/sysconfig/rhn/entitlement-cert.xml"
            self.cert = open(certFile, 'r').read()
        except:
            LOG.debug("Unable to read cert from %s" % (certFile))
            self.cert = None
        try:
            systemidFile = "/etc/sysconfig/rhn/systemid"
            self.systemid = open(systemidFile, 'r').read()
        except:
            LOG.debug("Unable to read systemid from %s" % (systemidFile))
            self.systemid = None
        self.username = None
        self.password = None
        self.parallel = 5
        self.fetchAll = False
        self.parallelFetchPkgs = None
        self.parallelFetchKickstarts = None
        self.skipProductList = ["rh-public", "k12ltsp", "education"]
        self.debug = False
        self.killcount = 0
        self.removeOldPackages = False
        self.rhnComm = None
        self.basePath = None
        self.channelSyncList = []
        self.verbose = False

    def setPassword(self, pword):
        LOG.debug("setPassword(%s)" % (pword))
        self.password = pword

    def getPassword(self):
        return self.password

    def setUsername(self, uname):
        LOG.debug("setUsername(%s)" % (uname))
        self.username = uname

    def getUsername(self):
        return self.username

    def setURL(self, url):
        LOG.debug("setURL(%s)" % (url))
        self.baseURL = url

    def getURL(self):
        return self.baseURL

    def setCert(self, cert):
        LOG.debug("setCert(%s)" % (cert))
        self.cert = cert

    def getCert(self):
        return self.cert

    def setSystemId(self, systemid):
        LOG.debug("setSystemId() with %s" % (systemid))
        self.systemid = systemid

    def getSystemId(self):
        return self.systemid

    def setParallel(self, parallel):
        LOG.debug("setParallel(%s)" % (parallel))
        self.parallel = parallel

    def getParallel(self):
        return self.parallel

    def setRemoveOldPackages(self, value):
        LOG.debug("setRemoveOldPackages(%s)" % (value))
        self.removeOldPackages = value

    def getRemoveOldPackages(self):
        return self.removeOldPackages

    def setFetchAllPackages(self, val):
        LOG.debug("setFetchAllPackages(%s)" % (val))
        self.fetchAll = val

    def getFetchAllPackages(self):
        return self.fetchAll

    def setSkipProductList(self, skipProductList):
        LOG.debug("setSkipProductList(%s)" % (skipProductList))
        self.skipProductList = skipProductList

    def getSkipProductList(self):
        return self.skipProductList

    def setNumOldPackagesToKeep(self, num):
        LOG.debug("setNumOldPackagesToKeep(%s)" % (num))
        self.numOldPkgsKeep = num

    def getNumOldPackagesToKeep(self):
        return self.numOldPkgsKeep

    def setBasePath(self, p):
        LOG.debug("setBasePath(%s)" % (p))
        self.basePath = p

    def getBasePath(self):
        return self.basePath

    def setVerbose(self, value):
        LOG.debug("setVerbose(%s)" % (value))
        self.verbose = value
    
    def getVerbose(self):
        return self.verbose

    def loadConfig(self, configFile):
        configInfo = {}
        if os.path.isfile(configFile):
            self.configFile = configFile
            try:
                import yaml
                raw = open(configFile).read()
                configInfo = yaml.load(raw)
            except ImportError:
                LOG.critical("Unable to load python module 'yaml'.")
                LOG.critical("Unable to parse config file: %s. Using command line options only." % (configFile))
                return False
            except Exception, e:
                LOG.critical("Exception: %s" % (e))
                LOG.critical("Unable to parse config file: %s. Using command line options only." % (configFile))
                return False
        else:
            LOG.info("Unable to read configuration file: %s" % (configFile))
            LOG.info("Will run with command line options only.")
            return False
        if configInfo.has_key("verbose"):
            self.setVerbose(configInfo["verbose"])
        if configInfo.has_key("all"):
            self.setFetchAllPackages(configInfo["all"])
        if configInfo.has_key("cert") and configInfo["cert"] is not None:
            cert = open(configInfo["cert"], 'r').read()
            self.setCert(cert)
        if configInfo.has_key("systemid") and configInfo["systemid"] is not None:
            sysid = open(configInfo["systemid"], 'r').read()
            self.setSystemId(sysid)
        if configInfo.has_key("parallel"):
            self.setParallel(int(configInfo["parallel"]))
        if configInfo.has_key("url"):
            self.setURL(configInfo["url"])
        if configInfo.has_key("removeold"):
            self.setRemoveOldPackages(configInfo["removeold"])
        if configInfo.has_key("num_old_pkgs_keep"):
            self.setNumOldPackagesToKeep(int(configInfo["num_old_pkgs_keep"]))
        if self.getFetchAllPackages() and self.getRemoveOldPackages():
            print "Conflicting options specified.  Fetch ALL packages AND remove older packages."
            print "This combination of options is not supported."
            print "Please remove one of these options and re-try"
            return False
        if configInfo.has_key("basepath"):
            self.setBasePath(configInfo["basepath"])
        if configInfo.has_key("channels"):
            self.setChannelSyncList(configInfo["channels"])
        return True

    def setChannelSyncList(self, l):
        self.channelSyncList = l

    def getChannelSyncList(self):
        return self.channelSyncList

    def deactivate(self):
        SATELLITE_URL = "%s/rpc/api" % (self.baseURL)
        client = getRhnApi(SATELLITE_URL, verbose=self.verbose)
        key = client.auth.login(self.username, self.password)
        retval = client.satellite.deactivateSatellite(self.systemid)
        print "retval from deactivation: %s"  % retval
        client.auth.logout(key)        
        print "Deactivated!"

    def activate(self):
        rhn = RHNTransport()    
        satClient = getRhnApi(self.baseURL + "/SAT", 
            verbose=self.verbose, transport=rhn)
        # First check if we are active
        active = False
        retval = satClient.authentication.check(self.systemid)
        LOG.debug("AUTH CHECK: %s " % str(retval))
        if (retval == 1):
            LOG.debug("We are activated ... continue!")
            active = True
        else:
            LOG.debug("Not active")
            
        if (not active): 
            if(not self.username or not self.password):
                raise SystemNotActivatedException()
            SATELLITE_URL = "%s/rpc/api" % (self.baseURL)
            client = RhnApi(SATELLITE_URL, verbose=self.verbose)
            key = client.auth.login(self.username, self.password)
            if not self.cert:
                self.cert = open(self.certFile, 'r').read()
            retval = client.satellite.activateSatellite(self.systemid, self.cert)
            LOG.debug("retval from activation: %s"  % retval)
            if (retval != 1):
                raise CantActivateException()
            client.auth.logout(key)        
            LOG.debug("Activated!")

    def stop(self):
        if (self.parallelFetchPkgs):
            self.parallelFetchPkgs.stop()
        if (self.parallelFetchKickstarts):
            self.parallelFetchKickstarts.stop()

    def checkChannels(self, channelsToSync):
        """
        Input:
            channelsToSync - list of channels to sync
        Output:
             list containing bad channel names
        """
        satDump = SatDumpClient(self.baseURL)
        channelFamilies = satDump.getChannelFamilies(self.systemid)
        badChannel = []
        for channelLabel in channelsToSync:
            found = False
            for d in channelFamilies.values():
                if channelLabel in d["channel_labels"]:
                    LOG.debug("Found %s under %s" % (channelLabel, d["label"]))
                    found = True
                    break
            if not found:
                LOG.debug("Unable to find %s, adding it to badChannel list" % (channelLabel))
                badChannel.append(channelLabel)
        return badChannel


    def getChannelLabels(self):
        labels = {}
        satDump = SatDumpClient(self.baseURL)
        channelFamilies = satDump.getChannelFamilies(self.systemid)
        for d in channelFamilies.values():
            if (d["label"] in self.skipProductList):
                continue
            labels[d["label"]] = d["channel_labels"]
        return labels

    def displayListOfChannels(self):
        labels = self.getChannelLabels()
        print("List of channels:")
        for lbl in labels:
            print("\nProduct : %s\n" % (lbl))
            for l in labels[lbl]:
                print("    %s" % (l))

    def syncKickstarts(self, channelLabel, savePath, verbose=0):
        """
        channelLabel - channel to sync kickstarts from
        savePath - path to save kickstarts, relative to basePath if basePath has been set
        verbose - if true display more output
        """
        if self.getBasePath():
            savePath = os.path.join(self.getBasePath(), savePath)
            LOG.info("Adjusting save path to: %s" % (savePath))

        startTime = time.time()
        satDump = SatDumpClient(self.baseURL, verbose=verbose)
        ksLabels = satDump.getKickstartLabels(self.systemid, [channelLabel])
        LOG.info("Found %s kickstart labels for channel %s" % (len(ksLabels[channelLabel]), channelLabel))
        ksFiles = []
        for ksLbl in ksLabels[channelLabel]:
            LOG.info("Syncing kickstart label: %s" % (ksLbl))
            metadata = satDump.getKickstartTreeMetadata(self.systemid, [ksLbl])
            LOG.info("Retrieved metadata on %s files for kickstart label: %s" % (len(metadata[ksLbl]["files"]), ksLbl))
            ksSavePath = os.path.join(savePath, ksLbl)
            for ksFile in metadata[ksLbl]["files"]:
                info = {}
                info["relative-path"] = ksFile["relative-path"]
                info["size"] = ksFile["file-size"]
                info["md5sum"] = ksFile["md5sum"]
                info["ksLabel"] = ksLbl
                info["channelLabel"] = channelLabel
                info["savePath"] = ksSavePath
                info["hashtype"] = ksFile["hashtype"]
                ksFiles.append(info)
        ksFetch = KickstartFetch(self.systemid, self.baseURL)
        numThreads = int(self.parallel)
        self.parallelFetchKickstarts = ParallelFetch(ksFetch, numThreads)
        self.parallelFetchKickstarts.addItemList(ksFiles)
        self.parallelFetchKickstarts.start()
        report = self.parallelFetchKickstarts.waitForFinish()
        endTime = time.time()
        LOG.info("Processed %s %s %s kickstart files, %s errors, completed in %s seconds" \
                % (channelLabel, ksLabels[channelLabel], report.successes, 
                    report.errors, (endTime-startTime)))
        return report

    def syncPackages(self, channelLabel, savePath, verbose=0):
        """
        channelLabel - channel to sync packages from
        savePath - path to save packages, relative to basePath if basePath has been set
        verbose - if true display more output
        """
        if self.getBasePath():
            savePath = os.path.join(self.getBasePath(), savePath)
            LOG.info("Adjusting save path to: %s" % (savePath))
        startTime = time.time()
        if channelLabel == "":
            LOG.critical("No channel label specified to sync, abort sync.")
            raise NoChannelLabelException()
        LOG.info("sync(%s, %s) invoked" % (channelLabel, verbose))
        satDump = SatDumpClient(self.baseURL, verbose=verbose)
        LOG.debug("*** calling product_names ***")
        packages = satDump.getChannelPackages(self.systemid, channelLabel)
        LOG.info("%s packages are available, getting list of short metadata now." % (len(packages)))
        pkgInfo = satDump.getShortPackageInfo(self.systemid, packages, filterLatest = not self.fetchAll)
        LOG.info("%s packages have been marked to be fetched" % (len(pkgInfo.values())))

        numThreads = int(self.parallel)
        LOG.info("Running in parallel fetch mode with %s threads" % (numThreads))
        pkgFetch = PackageFetch(self.systemid, self.baseURL, channelLabel, savePath)
        self.parallelFetchPkgs = ParallelFetch(pkgFetch, numThreads)
        self.parallelFetchPkgs.addItemList(pkgInfo.values())
        self.parallelFetchPkgs.start()
        report = self.parallelFetchPkgs.waitForFinish()
        LOG.debug("Attempting to fetch comps.xml info from RHN")
        self.fetchCompsXML(savePath, channelLabel)
        self.fetchUpdateinfo(savePath, channelLabel)
        endTime = time.time()
        LOG.info("Processed <%s> %s packages, %s errors, completed in %s seconds" \
                % (channelLabel, report.successes, report.errors, (endTime-startTime)))
        if self.removeOldPackages:
            LOG.info("Remove old packages from %s" % (savePath))
            self.runRemoveOldPackages(savePath)
        self.createRepo(savePath)
        self.updateRepo(os.path.join(savePath,"updateinfo.xml"),
                os.path.join(savePath,"repodata/"))
        return report
    
    def fetchCompsXML(self, savePath, channelLabel):
        ###
        # Fetch comps.xml, used by createrepo for "groups" info
        ###
        compsxml = ""
        try:
            self.rhnComm = RHNComm(self.baseURL, self.systemid)
            compsxml = self.rhnComm.getRepodata(channelLabel, "comps.xml")
        except GetRequestException, ge:
            if (ge.code == 404):
                LOG.info("Channel has no compsXml")
            else:
                raise ge
        if not savePath:
            savePath = channelLabel
        f = open(os.path.join(savePath, "comps.xml"), "w")
        f.write(compsxml)
        f.close()

    def fetchUpdateinfo(self, savePath, channelLabel):
        """
          Fetch updateinfo.xml.gz used by yum security plugin
        """
        import gzip
        updateinfo_gz = ""
        try:
            self.rhnComm = RHNComm(self.baseURL, self.systemid)
            updateinfo_gz = self.rhnComm.getRepodata(channelLabel, "updateinfo.xml.gz")
        except GetRequestException, ge:
            if (ge.code == 404):
                LOG.info("Channel has no Updateinfo")
            else:
                raise ge
        if not savePath:
            savePath = channelLabel
        fname = os.path.join(savePath, "updateinfo.xml.gz")
        f = open(fname, 'wb');
        f.write(updateinfo_gz)
        f.close()

        f = open(os.path.join(savePath,"updateinfo.xml"), 'w')
        f.write(gzip.open(fname, 'r').read())
        f.close()

    def createRepo(self, dir):
        startTime = time.time()
        status, out = commands.getstatusoutput('createrepo --update -g comps.xml %s' % (dir))

        class CreateRepoError:
            def __init__(self, output):
                self.output = output

            def __str__(self):
                return self.output

        if status != 0:
            raise CreateRepoError(out)
        endTime = time.time()
        LOG.info("createrepo on %s finished in %s seconds" % (dir, (endTime-startTime)))
        return status, out

    def updateRepo(self, updatepath, repopath):
        startTime = time.time()
        status, out = commands.getstatusoutput('modifyrepo %s %s' % (updatepath, repopath))
        class CreateRepoError:
            def __init__(self, output):
                self.output = output

            def __str__(self):
                return self.output

        if status != 0:
            raise CreateRepoError(out)
        endTime = time.time()
        LOG.info("updaterepo on %s finished in %s seconds" % (repopath, (endTime-startTime)))
        return status, out


