#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
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

import pymongo

# Python
import logging
import gzip
import os

# 3rd Party
import yum.comps
from yum.Errors import CompsException

# Pulp
from grinder.RepoFetch import YumRepoGrinder
from pulp import model
from pulp import repo_sync, upload
from pulp.api.base import BaseApi
#from pulp.api.package import PackageApi
from pulp.api.package_version import PackageVersionApi
from pulp.api.package_group import PackageGroupApi
from pulp.api.package_group_category import PackageGroupCategoryApi
from pulp.pexceptions import PulpException

log = logging.getLogger('pulp.api.repo')


class RepoApi(BaseApi):
    """
    API for create/delete/syncing of Repo objects
    """

    def __init__(self, config):
        BaseApi.__init__(self, config)

        #self.packageApi = PackageApi(config)
        self.packageVersionApi = PackageVersionApi(config)
        self.packageGroupApi = PackageGroupApi(config)
        self.packageGroupCategoryApi = PackageGroupCategoryApi(config)

        # TODO: Extract this to a config
        self.localStoragePath = config.get('paths', 'local_storage')

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
        Return dictionary of PackageVersion objects in this Repo, key is package name
        """
        repo = self.repository(id)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % id)
        return repo['packages']
    
    def packageversions(self, repoid, name):
        """
        Return list of PackageVersions objects for this repo and package name
        """
        repo = self.repository(repoid)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % repoid)
        if not repo["packages"].has_key(name):
            return None
        return repo["packages"][name]

    def packagegroups(self, id):
        """
        Return list of PackageGroup objects in this Repo
        """
        repo = self.repository(id)
        return repo['packagegroups']
    
    def packagegroupcategories(self, id):
        """
        Return list of PackageGroupCategory objects in this Repo
        """
        repo = self.repository(id)
        return repo['packagegroupcategories']
    
    def create(self, id, name, arch, feed):
        """
        Create a new Repository object and return it
        """
        r = model.Repo(id, name, arch, feed)
        self.objectdb.insert(r)
        return r

    def add_package_version(self, repoid, pv):
        """
        Adds the passed in package version to this repo
        """
        repo = self.repository(repoid)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % repoid)
        if not repo["packages"].has_key(pv['name']):
            repo["packages"][pv['name']] = []
        # TODO:  We might want to restrict PackageVersions we add to only
        #        allow 1 NEVRA per repo and require filename to be unique
        for item in repo["packages"][pv['name']]:
            if item['_id'] == pv['_id']:
                # No need to update repo, this PackageVersion is already under this repo
                return
        # Note:  A DBRef() for the objects '_id' is what's added in mongo
        #        This is a reference to the PackageVersion collection's object
        repo["packages"][pv['name']].append(pv)
        self.update(repo)

    def remove_package_version(self, repoid, pv):
        repo = self.repository(repoid)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % repoid)
        if not repo["packages"].has_key(pv['name']):
            raise PulpException("No Package with name: %s found in repo: %s" %
                    (pv['name'], repoid))
        for item in repo["packages"][pv['name']]:
            if item['name'] == pv['name'] and \
                item['version'] == pv['version'] and \
                item['epoch'] == pv['epoch'] and \
                item['release'] == pv['release'] and \
                item['arch'] == pv['arch']:
                    repo['packages'][pv['name']].remove(item)
                    if len(repo['packages'][pv['name']]) == 0:
                        # list is empty now, so cleanup and remove 
                        # it from the packages
                        del repo['packages'][pv['name']]
        self.update(repo)


    def sync(self, id):
        """
        Sync a repo from the URL contained in the feed
        """
        repo = self.repository(id)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % id)
        
        repo_source = model.RepoSource(repo['source'])
        repo_sync.sync(self.config, repo, repo_source)
        self.update(repo)

    def upload(self, id, pkginfo, pkgstream):
        """
        Store the uploaded package and associate to this repo
        """
        repo = self.repository(id)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % id)
        pkg_upload = upload.PackageUpload(self.config, repo, pkginfo, pkgstream)
        pkg_upload.upload()
        log.error("Upload success")
        self.update(repo)
        return True
