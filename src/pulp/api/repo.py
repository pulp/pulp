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


# Python
import logging
import gzip
import os

# 3rd Party
import pymongo
import yum.comps
from yum.Errors import CompsException

# Pulp
from grinder.RepoFetch import YumRepoGrinder
from pulp import model
from pulp import upload
from pulp.api import repo_sync
from pulp.api.base import BaseApi
from pulp.api.package import PackageApi
import pulp.api.repo_sync
from pulp.pexceptions import PulpException


log = logging.getLogger('pulp.api.repo')


class RepoApi(BaseApi):
    """
    API for create/delete/syncing of Repo objects
    """

    def __init__(self, config):
        BaseApi.__init__(self, config)

        self.packageApi = PackageApi(config)
        self.localStoragePath = config.get('paths', 'local_storage')
   
    def _get_indexes(self):
        return ["packages", "packagegroups", "packagegroupcategories"]

    def _get_unique_indexes(self):
        return ["id"]

    def _getcollection(self):
        return self.db.repos

    def update(self, repo):
        self.objectdb.save(repo, safe=True)

        if repo['sync_schedule']:
            pulp.api.repo_sync.update_schedule(self.config, repo)
        else:
            pulp.api.repo_sync.delete_schedule(self.config, repo)

        return repo

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
        
    def packages(self, id, name=None):
        """
        Return list of Package objects in this Repo
        """
        repo = self.repository(id)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % id)
        if (name == None):
            return repo['packages']
        else:
            matches = []
            packages = repo['packages']
            for package in packages.values():
                if (package['name'].index(name) >= 0):
                    matches.append(package)
            return matches
    
    def package_by_name(self, id, name):
        """
        Return matching Package object in this Repo
        """
        repo = self.repository(id)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % id)
        packages = repo['packages']
        for package in packages.values():
            log.error(package['name'])
            if (package['name'] == name):
                return package
    
    def add_package(self, repoid, packageid):
        """
        Adds the passed in package to this repo
        """
        repo = self.repository(repoid)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % repoid)
        package = self.packageApi.package(packageid)
        if (package == None):
            raise PulpException("No Package with id: %s found" % packageid)
        # TODO:  We might want to restrict Packages we add to only
        #        allow 1 NEVRA per repo and require filename to be unique
        self._add_package(repo, package)
        self.update(repo)

    def _add_package(self, repo, p):
        """
        Responsible for properly associating a Package to a Repo
        """
        packages = repo['packages']
        if (packages.has_key(p['id'])):
            # No need to update repo, this Package is already under this repo
            return
        packages[p['id']] = p           

    def remove_package(self, repoid, p):
        repo = self.repository(repoid)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % repoid)
        del repo["packages"][p['id']]
        self.update(repo)

    def remove_packagegroup(self, repoid, groupid):
        """
        Remove a packagegroup from a repo
        """
        repo = self.repository(repoid)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % repoid)
        if repo['packagegroups'].has_key(groupid):
            del repo['packagegroups'][groupid]
        self.update(repo)

    def update_packagegroup(self, repoid, pg):
        """
        Save the passed in PackageGroup to this repo
        """
        repo = self.repository(repoid)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % repoid)
        repo['packagegroups'][pg['id']] = pg
        self.update(repo)

    def update_packagegroups(self, repoid, pglist):
        """
        Save the list of passed in PackageGroup objects to this repo
        """
        repo = self.repository(repoid)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % repoid)
        for item in pglist:
            repo['packagegroups'][item['id']] = item
        self.update(repo)

    def packagegroups(self, id):
        """
        Return list of PackageGroup objects in this Repo
        """
        repo = self.repository(id)
        return repo['packagegroups']
    
    def packagegroup(self, repoid, groupid):
        """
        Return a PackageGroup from this Repo
        """
        repo = self.repository(repoid)
        if not repo['packagegroups'].has_key(groupid):
            return None
        return repo['packagegroups'][groupid]

    def remove_packagegroupcategory(self, repoid, categoryid):
        """
        Remove a packagegroupcategory from a repo
        """
        repo = self.repository(repoid)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % repoid)
        if repo['packagegroupcategories'].has_key(categoryid):
            del repo['packagegroupcategories'][categoryid]
        self.update(repo)
    
    def update_packagegroupcategory(self, repoid, pgc):
        """
        Save the passed in PackageGroupCategory to this repo
        """
        repo = self.repository(repoid)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % repoid)
        repo['packagegroupcategories'][pgc['id']] = pgc
        self.update(repo)
    
    def update_packagegroupcategories(self, repoid, pgclist):
        """
        Save the list of passed in PackageGroupCategory objects to this repo
        """
        repo = self.repository(repoid)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % repoid)
        for item in pgclist:
            repo['packagegroupcategories'][item['id']] = item
        self.update(repo)

    def packagegroupcategories(self, id):
        """
        Return list of PackageGroupCategory objects in this Repo
        """
        repo = self.repository(id)
        return repo['packagegroupcategories']

    def packagegroupcategory(self, repoid, categoryid):
        """
        Return a PackageGroupCategory object from this Repo
        """
        repo = self.repository(repoid)
        if not repo['packagegroupcategories'].has_key(categoryid):
            return None
        return repo['packagegroupcategories'][categoryid]

    def create(self, id, name, arch, feed, symlinks=False, sync_schedule=None):
        """
        Create a new Repository object and return it
        """
        r = model.Repo(id, name, arch, feed)
        r['sync_schedule'] = sync_schedule
        r['use_symlinks'] = symlinks
        self.insert(r)

        if sync_schedule:
            pulp.api.repo_sync.update_schedule(self.config, r)

        return r

    def sync(self, id):
        """
        Sync a repo from the URL contained in the feed
        """
        repo = self.repository(id)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % id)
        
        repo_source = repo['source']
        added_packages = repo_sync.sync(self.config, repo, repo_source)
        for p in added_packages:
            self._add_package(repo, p)
        self.update(repo)

    def upload(self, id, pkginfo, pkgstream):
        """
        Store the uploaded package and associate to this repo
        """
        repo = self.repository(id)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % id)
        pkg_upload = upload.PackageUpload(self.config, repo, pkginfo, pkgstream)
        pkg, repo = pkg_upload.upload()
        self._add_package(repo, pkg)
        self.update(repo)
        log.error("Upload success %s %s" % (pkg['id'], repo['id']))
        return True

    def all_schedules(self):
        '''
        For all repositories, returns a mapping of repository name to sync schedule.
        
        @rtype:  dict
        @return: key - repo name, value - sync schedule
        '''
        repo_api = RepoApi(self.config)
        all_repos = repo_api.repositories()

        result = {}
        for repo in all_repos:
            result[repo['id']] = repo['sync_schedule']

        return result

