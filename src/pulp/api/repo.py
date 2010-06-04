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
   
    def _get_indexes(self):
        return ["packages", "packagegroups", "packagegroupcategories"]

    def _get_unique_indexes(self):
        return ["id"]

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

    def translate_packagegroup(self, obj):
        """
        Translate a SON Document to an object that yum.comps.Comps can work with
        """
        # Main reason for doing this is that yum.comps expects the passed in 
        # object to support dot notation references, the returned SON document
        # does not support this, so yum.comps isn't able to read the info 
        #TODO: More work is needed in this method before output of groups will work
        pg = model.PackageGroup(obj['id'], obj['name'], obj['description'], 
                user_visible=obj['user_visible'], display_order=obj['display_order'],
                default=obj['default'], langonly=obj['langonly'])
        pg.groupid = obj['id']  
        pg.translated_name = {}
        for key in obj['translated_name']:
            pg.translated_name[key] = obj['translated_name'][key]
        pg.translated_description = {}
        for key in obj['translated_description']:
            pg.translated_description[key] = obj['translated_description']
        pg.mandatory_packages = {}
        for pkgname in obj['mandatory_package_names']:
            pg.mandatory_packages[pkgname] = 1 
        pg.optional_packages = {}
        for pkgname in obj['optional_package_names']:
            pg.optional_packages[pkgname] = 1
        pg.default_packages = {}
        for pkgname in obj['default_package_names']:
            pg.default_packages[pkgname] = 1
        pg.conditional_packages = {}
        for key in obj['conditional_package_names']:
            pg.conditional_packages[key] = obj['conditional_package_names'][key]
        return pg

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

    def translate_packagegroupcategory(self, obj):
        """
        Translate a SON Document to an object that yum.comps.Comps can work with
        """
        #TODO: More work is needed in this method before output of categories will work
        pgc = model.PackageGroupCategory(obj['id'], obj['name'], obj['description'], 
                display_order=obj['display_order'])
        pgc.categoryid = obj['id']
        pgc.translated_name = {}
        for key in obj['translated_name']:
            pgc.translated_name[key] = obj['translated_name'][key]
        pgc.translated_description = {}
        for key in obj['translated_description']:
            pgc.translated_description[key] = obj['translated_description'][key]
        pgc._groups = {}
        for groupid in obj['packagegroupids']:
            pgc._groups[groupid] = groupid
        return pgc

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
