#!/usr/bin/python 

import unittest
import os
import sys
sys.path.append("../src")
from grinder.grinder import Grinder
import rpmUtils.miscutils

class TestRemoveOldPackages(unittest.TestCase):
    testDir = "./package_test"
    url = "https://satellite.rhn.redhat.com"
    certpath = "/etc/sysconfig/rhn/entitlement-cert.xml"
    systemid = "/etc/sysconfig/rhn/systemid"

    def getGrinder(self):
        g = Grinder(self.url, 'username', 'password', 
            self.certpath, self.systemid, 1, 0)
        return g

    def test_runRemoveOldPackages(self):
        numOld = 1
        testDir = "./package_test"
        g = self.getGrinder()
        g.runRemoveOldPackages(testDir, numOld)
        rpms = g.getSortedListOfSyncedRPMs(testDir)
        for key in rpms:
            values = rpms[key]
            # remember we want to make sure we have at most
            # the current RPM and how ever many we specified in numOld
            assert(len(values) <= numOld + 1)

    def test_sortedListOfSyncedRPMs(self):
        g = self.getGrinder()
        rpms = g.getSortedListOfSyncedRPMs(self.testDir)
        for key in rpms:
            values = rpms[key]
            assert(self.isSorted(values))

    def isSorted(self, rpms):
        if len(rpms) < 2:
            return True
        for index in range(len(rpms) - 1):
            rpm1 = rpms[index]
            rpm2 = rpms[index+1]
            a = (rpm1["epoch"], rpm1["version"], rpm1["release"])
            b = (rpm2["epoch"], rpm2["version"], rpm2["release"])
            cmpVal = rpmUtils.miscutils.compareEVR(a,b)
            if cmpVal != 1:
                print "Failed on %s rpmUtils.miscutils.compareEVR %s" % (a,b)
                return False
        return True


def setupLogging():
    import logging
    logging.basicConfig(filename="output.log", level=logging.DEBUG,
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        datefmt='%m-%d %H:%M', filemode='w')

if __name__ == '__main__':
    setupLogging()
    if not os.path.isdir(TestRemoveOldPackages.testDir):
        print "Recommended usage:"
        print "Sync a large channel with a lot of old packages"
        print "Example: rhel-i386-server-5"
        print "Copy that synced channel to '%s'" % (TestRemoveOldPackages.testDir)
        print "Re-run this script"
        sys.exit(1)
    unittest.main()

