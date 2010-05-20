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
import os

import logging
import pymongo
from urlparse import urlparse

from grinder.RepoFetch import YumRepoGrinder

from pulp import model
from pulp.pexceptions import PulpException
from pulp.util import getRPMInformation
from pulp.util import chunks


log = logging.getLogger("pulp.api")
# log.setLevel(logging.DEBUG)

class BaseApi(object):
    def __init__(self):
        ####### Mongo DB ########
        self.connection = pymongo.Connection()
        self.db = self.connection._database
        self.collection = self.db.pulp_collection
        ## INDEXES
        self.objectdb = self._getcollection()
        self.objectdb.create_index([("id", pymongo.DESCENDING)])
        
    def _getcollection(self):
        return

    
    def clean(self):
        """
        Delete all the Objects in the database.  WARNING: Destructive
        """
        self.objectdb.remove()

    def update(self, object):
        """
        Write the object document to the database
        """
        self.objectdb.save(object)

    def delete(self, id):
        """
        Delete a single stored Object
        """
        self.objectdb.remove({'id': id})
        
class RepoApi(BaseApi):

    """
    API for create/delete/syncing of Repo objects
    """
    def __init__(self):
        BaseApi.__init__(self)
        # TODO: Extract this to a config
        self.LOCAL_STORAGE = "/var/lib/pulp/"
        self.packageApi = PackageApi()
        self.packageVersionApi = PackageVersionApi()

    def _getcollection(self):
        return self.db.repos
        
    def repositories(self):
        """
        Return a list of Repositories
        """
        return list(self.objectdb.find())
        
    def repository(self, id):
        """
        Return a single Repository object
        """
        return self.objectdb.find_one({'id': id})
        
    def packages(self, id):
        """
        Return list of Package objects in this Repo
        """
        repo = self.repository(id)
        return repo['packages']
    
    def create(self, id, name, arch, feed):
        """
        Create a new Repository object and return it
        """
        r = model.Repo(id, name, arch, feed)
        self.objectdb.insert(r)
        return r
        

        
    def sync(self, id):
        """
        Sync a repo from the URL contained in the feed
        """
        repo = self.repository(id)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % id)
        
        rs = model.RepoSource(repo['source'])
        if (rs.type == 'yum'):
            log.debug("Creating repo grinder: %s" % rs.url)
            yfetch = YumRepoGrinder(repo['id'], rs.url.encode('ascii', 'ignore'), 1)
            yfetch.fetchYumRepo(self.LOCAL_STORAGE)
            repo_dir = "%s/%s/" % (self.LOCAL_STORAGE, repo['id'])
            self._add_packages_from_dir(repo_dir, repo)
            self.update(repo)
            log.debug("fetched!")
        if (rs.type == 'local'):
            log.debug("Local URL: %s" % rs.url)
            local_url = rs.url
            if (not local_url.endswith('/')):
                local_url = local_url + '/'
            parts = urlparse(local_url)
            log.debug("PARTS: %s" % str(parts))
            self._add_packages_from_dir(parts.path, repo)
            self.update(repo)
            
        return
    
    def _add_packages_from_dir(self, dir, repo):
        dirList=os.listdir(dir)
        packages = repo['packages']
        package_count = 0
        for fname in dirList:
            if (fname.endswith(".rpm")):
                try:
                    info = getRPMInformation(dir + fname)
                    p = self.packageApi.create(info['name'], info['description'])
                    pv = self.packageVersionApi.create(p.id, info['epoch'], 
                        info['version'], info['release'], info['arch'])
                    for dep in info['requires']:
                        pv.requires.append(dep)
                    for dep in info['provides']:
                        pv.provides.append(dep)
                    p.versions.append(pv)
                    self.packageApi.update(p)
                    packages[p.id] = p
                    package_count = package_count + 1
                except Exception, e:
                    log.error("error reading package %s" % (dir + fname))
        log.debug("read [%s] packages" % package_count)

        
class PackageApi(BaseApi):

    def __init__(self):
        BaseApi.__init__(self)
        self.objectdb = self.db.packages

    def _getcollection(self):
        return self.db.packages
        
    def create(self, id, name):
        """
        Create a new Package object and return it
        """
        p = model.Package(id, name)
        self.objectdb.insert(p)
        return p
        
    def package(self, id, filter=None):
        """
        Return a single Package object
        """
        return self.objectdb.find_one({'id': id})

    def packages(self):
        """
        List all packages.  Can be quite large
        """
        return list(self.objectdb.find())
        
class PackageVersionApi(BaseApi):

    def __init__(self):
        BaseApi.__init__(self)
        self.objectdb = self.db.packageversions

    def _getcollection(self):
        return self.db.packageversions

    def create(self, packageid, epoch, version, release, arch):
        """
        Create a new PackageVersion object and return it
        """
        pv = model.PackageVersion(packageid, epoch, version, release, arch)
        self.objectdb.insert(pv)
        return pv
        
    def packageversion(self, id, filter=None):
        """
        Return a single PackageVersion object
        """
        return self.objectdb.find_one({'id': id})

    def packageversions(self):
        """
        List all packages.  Can be quite large
        """
        return list(self.objectdb.find())

        
class ConsumerApi(BaseApi):

    def __init__(self):
        BaseApi.__init__(self)
        self.objectdb = self.db.consumers
        # INDEXES
        self.objectdb.create_index([("packageids", pymongo.DESCENDING)])


    def _getcollection(self):
        return self.db.consumers

    
    def create(self, id, description):
        """
        Create a new Consumer object and return it
        """
        c = model.Consumer(id, description)
        self.objectdb.insert(c)
        return c
        
    def bulkcreate(self, consumers):
        """
        Create a set of Consumer objects in a bulk manner
        """
        ## Have to chunk this because of issue with PyMongo and network
        ## See: http://tinyurl.com/2eyumnc
        chunksize = 500
        chunked = chunks(consumers, chunksize)
        inserted = 0
        for chunk in chunked:
            self.objectdb.insert(chunk)
            inserted = inserted + chunksize
            print "Inserted: %s" % inserted

    def consumers(self):
        """
        List all consumers.  Can be quite large
        """
        return list(self.objectdb.find())

    def consumers(self):
        """
        List all consumers.  Can be quite large
        """
        return list(self.objectdb.find())
    
        
    def consumer(self, id):
        """
        Return a single Consumer object
        """
        return self.objectdb.find_one({'id': id})
    
    def consumerswithpackage(self, packageid):
        """
        List consumers using passed in packageid
        """
        return list(self.objectdb.find({"packageids":  packageid}))
