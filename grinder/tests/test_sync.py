import unittest
import logging
import os
import sys
import shutil
from grinder.RepoFetch import YumRepoGrinder
sys.path.append("../src")

class TestSync(unittest.TestCase):

    def test_yum_sync(self):
        testlabel = "test-label"
        cwd = os.getcwd()
        destdir = cwd + "/dest/"
        yfetch = YumRepoGrinder(testlabel, "http://mmccune.fedorapeople.org/pulp/", 1)
        yfetch.fetchYumRepo(destdir)
        repomd = destdir + "/" + testlabel + "/repodata/repomd.xml"
        assert(os.path.exists(repomd))
        shutil.rmtree(destdir)



    #def test_local_sync(self):
        #cwd = os.getcwd()
        #datadir = cwd + "/data/"
        #destdir = cwd + "/dest/"
        #print "Data dir! %s" % datadir
        
        #lfetch = LocalGrinder(repo['id'], rs.url, 1)
        #lfetch.fetchRepo(destdir)

        #repo = self.rapi.create('some-id','some name', 'i386', 
                                #'local:file://%s' % datadir)
                                
        #self.rapi.sync(repo.id)
        #found = self.rapi.repository(repo.id)
        #packages = found['packages']
        #assert(packages != None)
        #assert(len(packages) > 0)
        #print packages
        #p = packages.values()[0]
        #assert(p['versions'] != None)
