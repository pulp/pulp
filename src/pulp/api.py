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
import pymongo
import model
from util import getRPMInformation
from grinder.RepoFetch import YumRepoGrinder

from pymongo import Connection

class RepoApi(object):
    
    """
    API for create/delete/syncing of Repo objects
    """
    def __init__(self):
        ####### Mongo DB ########
        connection = Connection()
        self.db = connection._database
        self.collection = self.db.pulp_collection
        self.repos = self.db.repos
        # TODO: Extract this to a config
        self.LOCAL_STORAGE = "/var/lib/pulp/"

    def clean(self):
        """
        Delete all the Repos in the database.  WARNING: Destructive
        """
        self.repos.remove()

    def repositories(self):
        """
        Return a list of Repositories
        """
        return list(self.repos.find())
        
    def repository(self, id):
        """
        Return a single Repository object
        """
        return self.repos.find_one({'id': id})
        
    def packages(self, id):
        """
        Return list of Package objects in this Repo
        """
        repo = repository(id)
        return repo['packages']
        
    def update(self, repo):
        """
        Write the repository document to the database
        """
        self.repos.save(repo)
    
    def create(self, id, name, arch, feed):
        """
        Create a new Repository object and return it
        """
        r = model.Repo(id, name, arch, feed)
        self.repos.insert(r)
        return r
        

    def delete(self, id):
        """
        Delete a single Repository
        """
        self.repos.remove({'id': id})
        
    def sync(self, id):
        """
        Sync a repo from the URL contained in the feed
        """
        repo = self.repository(id)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % id)
        
        print "Creating repo grinder"
        yfetch = YumRepoGrinder(repo['id'], repo['feed'], 1)
        yfetch.fetchYumRepo(self.LOCAL_STORAGE)
        self._add_packages_from_dir(self.LOCAL_STORAGE, repo)
        self.update(repo)
        print "fetched!"
        return
    
    def _add_packages_from_dir(self, base_dir, repo):
        repo_dir = "%s/%s/" % (base_dir, repo['id'])
        dirList=os.listdir(repo_dir)
        packages = repo['packages']
        package_count = 0
        for fname in dirList:
            if (fname.endswith(".rpm")):
                info = getRPMInformation(repo_dir + fname)
                # print "rpm name: %s" % info['name']
                p = model.Package(info['name'], info['description'])
                packages[p.id] = p
                package_count = package_count + 1
        
        print "read [%s] packages" % package_count

        
        
