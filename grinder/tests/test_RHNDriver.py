import unittest

import os
import sys
sys.path.append("../src")
from grinder.GrinderCLI import RHNDriver
from grinder import GrinderLog
from test_RHNSync import TestRHNSync

def noOp():
    pass

class TestRHNDriver(unittest.TestCase):

    def __init__(self, arg):
        unittest.TestCase.__init__(self,arg)
        GrinderLog.setup(False)

    def test_loadConfigFileNoCLIOptions(self):
        """
        Test loading a config file and reading options when no CLI options are present
        """
        sys.argv = []
        sys.argv.append("./GrinderCLI.py")
        sys.argv.append("rhn")
        sys.argv.append("--config")
        sys.argv.append("./tests/config/testConfigA.yml")
        rhnDriver = RHNDriver()
        # We want to fake out _do_command, i.e. don't try to sync any channels
        setattr(rhnDriver, "_do_command", noOp)
        rhnDriver.main()
        rhnDriver._validate_options()
        testRhnSync = TestRHNSync("validateOptions")
        self.assertTrue(testRhnSync.validateOptions(rhnDriver.rhnSync))


    def test_loadConfigFileWithCLIOptions(self):
        """
        Test that CLI options take precedence over config file values
        """
        testAll = True
        url = "https://testFromCLIOptions.com"
        parallel = 299
        basePath = "/fromCLI/base/path"
        testPassword = "testPassword"
        testUsername = "testUsername"
        testRemoveold = False
        certFile = "/tmp/randomCertFile.grinderTests"
        f = open(certFile, 'w')
        testCertData = "This is a test of cert data from the CLI"
        f.write(testCertData)
        f.close()
        sysIdFile = "/tmp/randomSysIdFile.grinderTests"
        f = open(sysIdFile, 'w')
        testSysIdData = "This is a test of sysId data from the CLI"
        f.write(testSysIdData)
        f.close()

        sys.argv = []
        sys.argv.append("./GrinderCLI.py")
        sys.argv.append("rhn")
        sys.argv.append("--config")
        sys.argv.append("./tests/config/testConfigA.yml")
        if testAll:
            sys.argv.append("--all")
        sys.argv.append("--url")
        sys.argv.append(url)
        sys.argv.append("--parallel")
        sys.argv.append(parallel)
        sys.argv.append("--basepath")
        sys.argv.append(basePath)
        sys.argv.append("--systemid")
        sys.argv.append(sysIdFile)
        sys.argv.append("--cert")
        sys.argv.append(certFile)
        sys.argv.append("--password")
        sys.argv.append(testPassword)
        if testRemoveold:
            sys.argv.append("--removeold")
        sys.argv.append("--username")
        sys.argv.append(testUsername)
        try:
            rhnDriver = RHNDriver()
            # We want to fake out _do_command, i.e. don't try to sync any channels
            setattr(rhnDriver, "_do_command", noOp)
            rhnDriver.main()
            rhnDriver._validate_options()
            self.assertEquals(rhnDriver.rhnSync.getFetchAllPackages(), testAll)
            self.assertEquals(rhnDriver.rhnSync.getURL(), url)
            self.assertEquals(rhnDriver.rhnSync.getParallel(), parallel)
            self.assertEquals(rhnDriver.rhnSync.getBasePath(), basePath)
            self.assertEquals(rhnDriver.rhnSync.getSystemId(), testSysIdData)
            self.assertEquals(rhnDriver.rhnSync.getCert(), testCertData)
            self.assertEquals(rhnDriver.rhnSync.getPassword(), testPassword)
            self.assertEquals(rhnDriver.rhnSync.getRemoveOldPackages(), testRemoveold)
            self.assertEquals(rhnDriver.rhnSync.getUsername(), testUsername)
        finally:
            os.remove(certFile)
            os.remove(sysIdFile)

if __name__ == "__main__":
    unittest.main()



