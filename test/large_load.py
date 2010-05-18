#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Mike McCune
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

import optparse
import sys
import time
import logging
import unittest
import os
import fileinput

sys.path.append("../src")
from pulp.api import RepoApi
from pulp.api import PackageApi
from pulp.api import ConsumerApi
from pulp.model import Package
from pulp.model import Consumer
from pulp.util import random_string

class LargeLoad(unittest.TestCase):
    
    """
    Util for loading large amounts of data through our API
    """
    def __init__(self, dir_list_path):
        self.rapi = RepoApi()
        self.papi = PackageApi()
        self.capi = ConsumerApi()
        self.dirlist = []
        if (dir_list_path != None):
            for line in fileinput.input(dir_list_path):
                line = line.rstrip()
                self.dirlist.append(line)

    def clean(self):
        self.rapi.clean()
        self.papi.clean()
        self.capi.clean()
        
    def create_repos(self):
        print "RPMDIRS: %s" % self.dirlist
        for rdir in self.dirlist:
            repo = self.rapi.create(rdir,'test repo: %s' % rdir, \
                'i386', 'local:file://%s' % rdir)
            self.rapi.sync(repo.id)
        
        print "[%s] repos created" % len(self.dirlist)
    
    def create_consumers(self):
        last_desc = None
        last_id = None
        for i in range(1000):
            c = self.capi.create(random_string(), random_string())
            #for pid in r.packages:
            #    c.packages[pid] = r.packages[pid]
            #    c.packageids.append(pid)
            if (i % 100 == 0):
                print "Inserted [%s] consumers" % i
                p = Package('random-package', 'random package to be found')
                c.packages[p.id] = p
            last_desc = c.description
            last_id = c.id



parser = optparse.OptionParser()
parser.add_option('--dirlist', dest='dirlist', 
                 action='store', help='File containing list of directories containing the repos you wish to use for this test')
parser.add_option('--clean', dest='clean', action='store_true', help='Clean db')
cmdoptions, args = parser.parse_args()
dirlist = cmdoptions.dirlist
clean = cmdoptions.clean

if (clean):
    ll = LargeLoad(None)
    ll.clean()
    exit("cleaned the databases")

if (dirlist == None):
    exit("ERROR: --dirlist <path-to-txt-file> is required.  Specify a txt file with a list of dirs you wish to use.")


console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.DEBUG)
logging.getLogger('pulp.api').addHandler(console)

ll = LargeLoad(dirlist)


ll.create_repos()
repos = ll.rapi.repositories()
packages = ll.papi.packages()

print "number of repos: %s" % len(list(repos))
print "number of packages: %s" % len(packages)
ll.create_consumers()
# ll.find_consumer()
# ll.find_repo()
# ll.find_consumers_with_package()

           

