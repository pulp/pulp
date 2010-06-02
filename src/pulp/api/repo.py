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
from pulp import repo_sync
from pulp.api.base import BaseApi
from pulp.api.package import PackageApi
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

        self.packageApi = PackageApi(config)
        self.packageVersionApi = PackageVersionApi(config)
        self.packageGroupApi = PackageGroupApi(config)
        self.packageGroupCategoryApi = PackageGroupCategoryApi(config)

        # TODO: Extract this to a config
        # self.localStoragePath = config.get('paths', 'local_storage')
        self.localStoragePath = '/var/lib/pulp'

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
        
        repo_source = model.RepoSource(repo['source'])
        repo_sync.sync(self.config, repo, repo_source)
        self.update(repo)
