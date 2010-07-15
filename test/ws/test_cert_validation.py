import os
import unittest
from pulptools.connection import Restlib

class TestApi(unittest.TestCase):
    
    def test_cert_validation(self):
        my_dir = os.path.abspath(os.path.dirname(__file__))
        keypath = my_dir + '/../unit/data/test_key.pem'
        certpath = my_dir + '/../unit/data/test_cert.pem'
        
        failed = False
        out = None
        try:
            rl = Restlib('localhost', 8811, '/test/invalid-id/', 
                         cert_file=certpath, key_file=keypath)
            out = rl.request_get('auth/')
        except Exception, e:
            failed = True
        self.assertTrue(failed)
        self.assertTrue(out == None)
         
        rl = Restlib('localhost', 8811, '/test/fb12d975-1f33-4b34-8ac9-0adb6089fb87/', 
             cert_file=certpath, key_file=keypath)
        out = rl.request_get('auth/')
        print "Valid request output: %s" % out
        self.assertTrue(out != None)
        
        



