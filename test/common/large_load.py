#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

import optparse
import sys
import time
import logging
import unittest
import os
import fileinput
import random
import copy


srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src"
sys.path.insert(0, srcdir)

from pulp.server.api.repo import RepoApi
from pulp.server.api.package import PackageApi
from pulp.server.api.consumer import ConsumerApi
from pulp.server.db.model import Consumer
from pulp.server.util import random_string
import pulp.server.util
from testutil import create_package
from pulp.client.utils import generatePakageProfile

TEST_PACKAGE_ID = 'random-package'

class LargeLoad(unittest.TestCase):

    """
    Util for loading large amounts of data through our API
    """
    def __init__(self, dir_list_path, numconsumers, config):
        self.config = config
        self.rapi = RepoApi()
        self.papi = PackageApi()
        self.capi = ConsumerApi()
        self.numconsumers = numconsumers
        self.dirlist = []
        if (dir_list_path != None):
            for line in fileinput.input(dir_list_path):
                line = line.rstrip()
                self.dirlist.append(line)

    def clean(self):
        self.rapi.clean()
        self.papi.clean()
        self.capi.clean()
        # db = self.rapi.collection
        # self.rapi.collection.database.connection.drop_database(db)

    def create_repos(self):
        print "RPMDIRS: %s" % self.dirlist
        numrepos = 0
        for rdir in self.dirlist:
            id = rdir.replace('/', '.')
            repo = self.rapi.create(id, 'test repo: %s' % rdir, \
                'i386', 'file://%s' % rdir)
            self.rapi._sync(repo['id'])
            numrepos = numrepos + 1

        return numrepos

    def add_package(self, profile, package):
        info = {
            'name'          : package['name'],
            'version'       : package['version'],
            'release'       : package['release'],
            'epoch'         : package['epoch'] or "",
            'arch'          : package['arch'],
        }
        profile.append(info)


    def create_consumers(self):
        last_desc = None
        last_id = None
        repos = self.rapi.repositories()
        consumers = []
        randomPackage = create_package(self.papi, TEST_PACKAGE_ID)
        repo = random.choice(repos)
        packages = repo['packages']
        packageProfile = generatePakageProfile(packages.values())
        packageProfileRand = copy.deepcopy(packageProfile)
        self.add_package(packageProfileRand, randomPackage)
        for i in range(self.numconsumers):
            c = Consumer(random_string(), random_string())
            start = time.time()
            if (i % 100 == 0):
                c['package_profile'] = packageProfileRand
            else:
                c['package_profile'] = packageProfile

            last_desc = c.description
            last_id = c.id
            consumers.append(c)
            if (i % 100 == 0):
                repo = random.choice(repos)
                packages = repo['packages']
                packageProfile = generatePakageProfile(packages.values())

        print "BULK INSERTING length: %s" % len(consumers)
        self.capi.bulkcreate(consumers)
        print "Done bulk inserting"

        return last_desc, last_id


    def find_consumer(self, last_id):
        # Get entire list.  Make sure its not too slow.
        # When we initially were storing the entire package in the 
        # consumer object this call would blow out all the ram on a 8GB box
        consumers = self.capi.consumers()
        print "consumers!"
        c = consumers[0]
        print "C: %s" % c['package_profile']
        # assert(len(consumers) == self.numconsumers)
        packages = self.capi.packages(c['id'])

        randomPackage = random.choice(packages)
        p = ll.papi.package_by_ivera(randomPackage['name'],
                                     randomPackage['version'],
                                     randomPackage['epoch'],
                                     randomPackage['release'],
                                     randomPackage['arch'])
        assert(p != None)
        c2 = self.capi.consumer(last_id)
        assert(c2 != None)
        print "Searching for all consumers with %s package id" % TEST_PACKAGE_ID
        cwithp = ll.capi.consumers_with_package_names([TEST_PACKAGE_ID])
        print "Found [%s] consumers with packageid: [%s]" % (len(cwithp), TEST_PACKAGE_ID)


parser = optparse.OptionParser()
parser.add_option('--dirlist', dest='dirlist',
                 action='store', help='File containing list of directories containing the repos you wish to use for this test')
parser.add_option('--numconsumers', dest='numconsumers',
                 action='store', default=1000, help='Number of consumers you want to load')

parser.add_option('--clean', dest='clean', action='store_true', help='Clean db')
parser.add_option('--config', dest='config', action='store', help='Configuration file',
                  default="../../etc/pulp/pulp.conf")
parser.add_option('--skiprepos', dest='skiprepos', action='store_true', help='Skip repo imports')
parser.add_option('--skipclean', dest='skipclean', action='store_true', help='Skip clean')

cmdoptions, args = parser.parse_args()
dirlist = cmdoptions.dirlist
clean = cmdoptions.clean
numconsumers = int(cmdoptions.numconsumers)
skiprepos = cmdoptions.skiprepos
skipclean = cmdoptions.skipclean
print "Attempting to load configuration from: %s" % (cmdoptions.config)
pulp.server.config.add_config_file(cmdoptions.config)
config = pulp.server.config

if (clean):
    ll = LargeLoad(None, None, dict())
    ll.clean()
    exit("cleaned the databases")

if (dirlist == None):
    exit("ERROR: --dirlist <path-to-txt-file> is required.  Specify a txt file with a list of dirs you wish to use.")


console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.DEBUG)
# logging.getLogger('pulp.api').addHandler(console)
# logging.getLogger('pulp.api').setLevel(logging.DEBUG)

## Start timing
start = time.time()
ll = LargeLoad(dirlist, numconsumers, config)
if (not skipclean):
    ll.clean()
cleanTime = time.time() - start

start = time.time()
if (not skiprepos):
    ll.create_repos()
repos = ll.rapi.repositories()
numrepos = len(repos)
packages = ll.papi.packages()
repoTime = time.time() - start

print "number of repos: %s" % len(list(repos))
print "number of packages: %s" % len(packages)
start = time.time()
last_desc, last_id = ll.create_consumers()
consumerCreateTime = time.time() - start
print "Done creating consumers.  Listing all of them"
start = time.time()
ll.find_consumer(last_id)
consumerSearchTime = time.time() - start
# ll.find_repo()
# ll.find_consumers_with_package()

numpackages = len(ll.papi.packages())
print "Your database now has [%s] repositories with [%s] total packages and [%s] consumers" \
      % (numrepos, numpackages, numconsumers)

print "Timings: cleanTime        : [%s]" % cleanTime
print "repo create and list time : [%s]" % repoTime
print "consumer create time      : [%s]" % consumerCreateTime
print "consumer find time        : [%s]" % consumerSearchTime
