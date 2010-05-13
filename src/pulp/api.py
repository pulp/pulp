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

log = logging.getLogger("pulp.api")

class BaseApi(object):
    def __init__(self):
        ####### Mongo DB ########
        connection = pymongo.Connection()
        self.db = connection._database
        self.collection = self.db.pulp_collection
    

class RepoApi(BaseApi):

    """
    API for create/delete/syncing of Repo objects
    """
    def __init__(self):
        BaseApi.__init__(self)
        self.repodb = self.db.repos
        # TODO: Extract this to a config
        self.LOCAL_STORAGE = "/var/lib/pulp/"
        self.packageApi = PackageApi()

    def clean(self):
        """
        Delete all the Repos in the database.  WARNING: Destructive
        """
        self.repodb.remove()

    def repositories(self):
        """
        Return a list of Repositories
        """
        return list(self.repodb.find())
        
    def repository(self, id):
        """
        Return a single Repository object
        """
        return self.repodb.find_one({'id': id})
        
    def packages(self, id):
        """
        Return list of Package objects in this Repo
        """
        repo = self.repository(id)
        return repo['packages']
        
    def update(self, repo):
        """
        Write the repository document to the database
        """
        self.repodb.save(repo)
    
    def create(self, id, name, arch, feed):
        """
        Create a new Repository object and return it
        """
        r = model.Repo(id, name, arch, feed)
        self.repodb.insert(r)
        return r
        

    def delete(self, id):
        """
        Delete a single Repository
        """
        self.repodb.remove({'id': id})
        
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
            yfetch = YumRepoGrinder(repo['id'], rs.url, 1)
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
                except:
                    log.error("error reading package %s" % (dir + fname))
                # print "rpm name: %s" % info['name']
                p = self.packageApi.create(info['name'], info['description'])
                packages[p.id] = p
                package_count = package_count + 1
        
        log.debug("read [%s] packages" % package_count)

        
        
class PackageApi(BaseApi):

    def __init__(self):
        BaseApi.__init__(self)
        self.packagesdb = self.db.packages
    
    def create(self, id, name):
        """
        Create a new Package object and return it
        """
        p = model.Package(id, name)
        self.packagesdb.insert(p)
        return p

    def packages(self):
        """
        List all packages.  Can be quite large
        """
        return list(self.packagesdb.find())
