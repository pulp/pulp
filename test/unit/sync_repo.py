#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
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
import random


sys.path.append("../src")
from pulp.api.repo import RepoApi
from pulp.api.package import PackageApi
from pulp.api.consumer import ConsumerApi
from pulp.model import Package
from pulp.model import Consumer
from pulp.util import randomString


TEST_PACKAGE_ID = 'random-package'

class SyncRepo(object):
    
    """
    Util for loading a repo of data through our API
    """
    def __init__(self, dir_list_path):
        self.rapi = RepoApi()
        self.dirlist = []
        if (dir_list_path != None):
            for line in fileinput.input(dir_list_path):
                line = line.rstrip()
                self.dirlist.append(line)

    def clean(self):
        self.rapi.clean()
        db = self.rapi.db
        self.rapi.connection.drop_database(db)
        
    def create_repos(self):
        print "RPMDIRS: %s" % self.dirlist
        numrepos = 0
        for rdir in self.dirlist:
            id = rdir.replace('/', '.')
            repo = self.rapi.create(id,'test repo: %s' % rdir, \
                'i386', 'local:file://%s' % rdir)
            self.rapi.sync(repo.id)
            numrepos = numrepos + 1
        return numrepos
    


if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option('--dirlist', dest='dirlist', 
                 action='store', help='File containing list of directories containing the repos you wish to use for this test')
    parser.add_option('--clean', dest='clean', action='store_true', help='Clean db')
    cmdoptions, args = parser.parse_args()
    dirlist = cmdoptions.dirlist
    clean = cmdoptions.clean

    if (clean):
        sr = SyncRepo(None)
        sr.clean()
        exit("cleaned the databases")

    if (dirlist == None):
        exit("ERROR: --dirlist <path-to-txt-file> is required.  Specify a txt file with a list of dirs you wish to use.")

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    logging.getLogger('pulp.api').addHandler(console)
    logging.getLogger('pulp.api').setLevel(logging.DEBUG)
    start = time.time()
    sr = SyncRepo(dirlist)
    sr.clean()
    numrepos = sr.create_repos()
    end = time.time()
    print "Created %s repos" % (numrepos)
    repos = sr.rapi.repositories()
    num_packages = 0
    for r in repos:
        num_packages += len(r["packages"])
        print "Repo <%s> has %s packages" % (r["id"], len(r["packages"]))
    print "number of packages: %s" % (num_packages)
    print "Your database now has [%s] repositories with [%s] total packages" \
      % (len(repos), num_packages)
           
    print "Took %s seconds" % (end - start)

