import unittest

import sys
sys.path.append("../src/")
from grinder.RHNSync import RHNSync
from grinder import GrinderLog


class TestRHNSync(unittest.TestCase):

    def __init__(self, arg):
        unittest.TestCase.__init__(self,arg)
        GrinderLog.setup(False)

    def test_loadConfig(self):
        """
        Test loading a config file supplies correct values
        """
        configFile = "./tests/config/testConfigA.yml"
        rhnSync = RHNSync()
        self.assertTrue(rhnSync.loadConfig(configFile))
        self.assertTrue(self.validateOptions(rhnSync))

    def validateOptions(self, rhnSync):
        self.assertEqual(rhnSync.getURL(), "http://testConfigValueFromConfigFile.com")
        self.assertEqual(rhnSync.getCert(), "This is a test entitlement file\n")
        self.assertEqual(rhnSync.getSystemId(), "This is a test systemid file\n")
        self.assertEqual(rhnSync.getVerbose(), False)
        self.assertEqual(rhnSync.getFetchAllPackages(), False)
        self.assertEqual(rhnSync.getParallel(), 99)
        self.assertEqual(rhnSync.getRemoveOldPackages(), False)
        self.assertEqual(rhnSync.getNumOldPackagesToKeep(), 2)
        self.assertEqual(rhnSync.getBasePath(), "/base/path/")
        channels = rhnSync.getChannelSyncList()
        expectedChannels = [{"label":"fred", "relpath":"/rel/path/fred"}, 
                {"label":"ethel", "relpath":"/rel/path/ethel"}, 
                {"label":"foo", "relpath":"/rel/path/foo"}]
        for c in expectedChannels:
            self.assertTrue(c in channels)
        return True

if __name__ == '__main__':
    unittest.main()
