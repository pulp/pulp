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
from pulp.api.package import PackageApi
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

        self.packageApi = PackageApi()
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
        return repo['packages']
    
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
        packages = repo['packages']
        package_count = 0
        for fname in dirList:
            if (fname.endswith(".rpm")):
                try:
                    info = getRPMInformation(dir + fname)
                    p = self.packageApi.package(info['name'])
                    if not p:
                        p = self.packageApi.create(info['name'], info['description'])
                    pv = self.packageVersionApi.create(p["packageid"], info['epoch'], 
                        info['version'], info['release'], info['arch'])
                    for dep in info['requires']:
                        pv.requires.append(dep)
                    for dep in info['provides']:
                        pv.provides.append(dep)
                    self.packageVersionApi.update(pv)
                    p["versions"].append(pv)
                    self.packageApi.update(p)
                    packages[p["packageid"]] = p
                    package_count = package_count + 1
                except Exception, e:
                    log.debug("Exception = %s" % (traceback.format_exc()))
                    log.error("error reading package %s" % (dir + fname))
        log.debug("read [%s] packages" % package_count)
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
