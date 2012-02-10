# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import logging

# Pulp
from pulp.server.api.base import BaseApi
from pulp.server.auditing import audit
from pulp.server.db import model
from pulp.server.event.dispatcher import event
from pulp.server.exceptions import PulpException
from pulp.common.util import encode_unicode


log = logging.getLogger(__name__)

filter_fields = model.Filter(None, None, None, None).keys()


class FilterApi(BaseApi):

    def _getcollection(self):
        return model.Filter.get_collection()

    def _getRepoCollection(self):
        return model.Repo.get_collection()

    @audit()
    def create(self, id, type, description=None, package_list=[]):
        """
        Create a new Filter object and return it
        """
        id = encode_unicode(id)
        filter = self.filter(id)
        if filter is not None:
            raise PulpException("A Filter with id %s already exists" % id)

        f = model.Filter(id, type, description, package_list)
        self.collection.insert(f, safe=True)
        f = self.filter(f["id"])
        return f


    @audit()
    def delete(self, id):
        """
        Delete filter object based on "id" key
        """
        filter = self.filter(id)
        if not filter:
            log.error("Filter id [%s] not found " % id)
            return
        associated_repo_ids = self.find_associated_repos(id)
        if not associated_repo_ids:
            self.collection.remove({'id' : id}, safe=True)
        else:
            self.remove_association_with_repos(id, associated_repo_ids)
            self.collection.remove({'id' : id}, safe=True)

    def filters(self, spec=None, fields=None):
        """
        Return a list of Filters
        """
        return list(self.collection.find(spec=spec, fields=fields))


    def filter(self, id, fields=None):
        """
        Return a single Filter object
        """
        return self.collection.find_one({'id': id})

    @event(subject='filter.updated.content')
    @audit()
    def add_packages(self, id, packages=[]):
        '''
         Add packages to a filter
         @param id: filter id
         @param packages: packages
        '''
        filter = self.filter(id)
        for package in packages:
            if package not in filter['package_list']:
                filter['package_list'].append(package)
        self.collection.save(filter, safe=True)
        log.info("Successfully added packages %s to filter %s" % (packages, id))

    @event(subject='filter.updated.content')
    @audit()
    def remove_packages(self, id, packages=[]):
        '''
         Remove packages from a filter
         @param id: filter id
         @param packages: packages
        '''
        filter = self.filter(id)
        for package in packages:
            if package in filter['package_list']:
                filter['package_list'].remove(package)
        self.collection.save(filter, safe=True)
        log.info("Successfully removed packages %s from filter %s" % (packages, id))

    @audit()
    def clean(self):
        """
        Delete all the Filter objects in the database.  
        WARNING: Destructive
        """
        found = self.filters(fields=["id"])
        for f in found:
            self.delete(f["id"])


    def find_associated_repos(self, id):
        """
        Find all the associated repos
        """
        associated_repo_ids = []
        repo_db = self._getRepoCollection()
        associated_repos = list(repo_db.find({'filters' : id}, fields=['id']))
        for repo in associated_repos:
            associated_repo_ids.append(repo['id'])
        return associated_repo_ids


    def remove_association_with_repos(self, id, repoids):
        repo_db = self._getRepoCollection()
        for repoid in repoids:
            repo = repo_db.find_one({'id' : repoid})
            filters = repo['filters']
            filters.remove(id)
            repo['filters'] = filters
            repo_db.save(repo, safe=True)
