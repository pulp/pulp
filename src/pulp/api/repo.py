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
import time
import traceback
import logging
import gzip
import os
from urlparse import urlparse

# 3rd Party
import yum.comps
from yum.Errors import CompsException

# Pulp
from grinder.RepoFetch import YumRepoGrinder
from pulp import model
from pulp.api.base import BaseApi
#from pulp.api.package import PackageApi
from pulp.api.package_version import PackageVersionApi
from pulp.api.package_group import PackageGroupApi
from pulp.api.package_group_category import PackageGroupCategoryApi
from pulp.pexceptions import PulpException
from pulp.util import getRPMInformation

log = logging.getLogger('pulp.api.repo')


class RepoApi(BaseApi):
    """
    API for create/delete/syncing of Repo objects
    """

    def __init__(self):
        BaseApi.__init__(self)
        #self.packageApi = PackageApi()
        self.packageVersionApi = PackageVersionApi()
        self.packageGroupApi = PackageGroupApi()
        self.packageGroupCategoryApi = PackageGroupCategoryApi()

        # TODO: Extract this to a config
        self.localStoragePath = "/var/lib/pulp/"

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
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % id)
        return repo['packages']
    
    def package(self, repoid, packageid):
        repo = self.repository(repoid)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % repoid)
        if not repo["packages"].has_key(packageid):
            return None
        return repo["packages"][packageid]

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

    def create_package(self, repoid, packageid, description):
        repo = self.repository(repoid)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % repoid)
        p = model.Package(repoid, packageid, description)
        repo["packages"][packageid] = p
        self.update(repo)
        return repo["packages"][packageid]

    def remove_package(self, repoid, packageid):
        repo = self.repository(repoid)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % repoid)
        if not repo["packages"].has_key(packageid):
            raise PulpException("No Package with id: %s found in repo: %s" %
                    (packageid, repoid))
        del repo["packages"][packageid]
        self.update(repo)

    def remove_packages(self, repoid):
        repo = self.repository(repoid)
        if (repo == None):
            raise PulpException("No Repo with id: %s found" % repoid)
        repo["packages"] = {}
        self.update(repo)

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
            yfetch.fetchYumRepo(self.localStoragePath)
            repo_dir = "%s/%s/" % (self.localStoragePath, repo['id'])
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
            
    def _add_packages_from_dir(self, dir, repo):
        dirList = os.listdir(dir)
        package_count = 0
        #TODO:  Do we want to traverse multiple directories, or should this
        #       be locked down to a single directory traversal?  
        #       How will this impact comps.xml and repodata if we allow import from
        #       multiple directories into a single pulp repo?
        startTime = time.time()
        for fname in dirList:
            if (fname.endswith(".rpm")):
                startTimeA = time.time()
                try:
                    info = getRPMInformation(dir + fname)
                    if repo["packages"].has_key(info['name']):
                        p = repo["packages"][info['name']]
                    else:
                        p = model.Package(repo['id'], info['name'], info['description'])
                        repo["packages"][p['packageid']] = p
                    # TODO: 
                    pv = self.packageVersionApi.create(p["packageid"], info['epoch'],
                        info['version'], info['release'], info['arch'])
                    for dep in info['requires']:
                        pv.requires.append(dep)
                    for dep in info['provides']:
                        pv.provides.append(dep)
                    self.packageVersionApi.update(pv)
                    p["versions"].append(pv)
                    package_count = package_count + 1
                    #log.debug("Repo <%s> added package <%s> with %s versions" %
                    #        (repo["id"], p["packageid"], len(p["versions"])))
                    endTimeA = time.time()
                    #log.debug("%s Repo <%s> added package %s %s:%s-%s-%s in %s seconds" % 
                    #        (package_count, repo["id"], p["packageid"], info['epoch'], 
                    #            info['version'], info['release'], info['arch'], 
                    #            (endTimeA - startTimeA)))
                except Exception, e:
                    log.debug("%s" % (traceback.format_exc()))
                    log.error("error reading package %s" % (dir + fname))
                endTime = time.time()
        log.debug("Repo: %s read [%s] packages took %s seconds" % (repo['id'], package_count, endTime - startTime))
        self._read_comps_xml(dir, repo)

    def _read_comps_xml(self, dir, repo):
        """
        Reads a comps.xml or comps.xml.gz under repodata from dir
        Loads PackageGroup and Category info our db
        """
        compspath = os.path.join(dir, 'repodata/comps.xml')
        compsxml = None
        if os.path.isfile(compspath):
            compsxml = open(compspath, "r")
        else:
            compspath = os.path.join(dir, 'repodata/comps.xml.gz')
            if os.path.isfile(compspath):
                compsxml = gzip.open(compspath, 'r')
        if not compsxml:
            log.info("Not able to find a comps.xml(.gz) to read")
            return False
        log.info("Reading comps info from %s" % (compspath))
        repo['comps_xml_path'] = compspath
        try:
            comps = yum.comps.Comps()
            comps.add(compsxml)
            for c in comps.categories:
                ctg = self.packageGroupCategoryApi.create(c.categoryid, 
                        c.name, c.description, c.display_order)
                groupids = [grp for grp in c.groups]
                ctg.packagegroupids.extend(groupids)
                ctg.translated_name = c.translated_name
                ctg.translated_description = c.translated_description
                self.packageGroupCategoryApi.update(ctg)
                repo['packagegroupcategories'][ctg.categoryid] = ctg
            for g in comps.groups:
                grp = self.packageGroupApi.create(g.groupid, g.name, g.description,
                        g.user_visible, g.display_order, g.default, g.langonly)
                grp.mandatory_package_names.extend(g.mandatory_packages.keys())
                grp.optional_package_names.extend(g.optional_packages.keys())
                grp.default_package_names.extend(g.default_packages.keys())
                grp.conditional_package_names = g.conditional_packages
                grp.translated_name = g.translated_name
                grp.translated_description = g.translated_description
                self.packageGroupApi.update(grp)
                repo['packagegroups'][grp.groupid] = grp
            log.info("Comps info added from %s" % (compspath))
        except CompsException:
            log.error("Unable to parse comps info for %s" % (compspath))
            return False
        return True
