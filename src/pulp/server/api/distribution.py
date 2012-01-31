# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
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
import os
import shutil

from pulp.server.api.base import BaseApi
from pulp.server.auditing import audit
from pulp.server.db import model
from pulp.server.event.dispatcher import event
from pulp.server.exceptions import PulpException
from pulp.server import config
from pulp.server import util

log = logging.getLogger(__name__)

distribution_fields = model.Distribution(None, None, None, None, None, None, None, [], None).keys()

class DistributionHasReferences(Exception):

    MSG = 'distribution [%s] has references, delete not permitted'

    def __init__(self, id):
        Exception.__init__(self, self.MSG % id)

class DistributionApi(BaseApi):

    def _getcollection(self):
        return model.Distribution.get_collection()

    @audit(params=["id"])
    def create(self, id, description, relativepath, family=None, variant=None,
               version=None, timestamp=None, files=[], arch=None, repoids=[]):
        """
        Create a new Distribution object and return it
        """
        d = self.distribution(id)
        if d:
            log.info("Distribution with id %s already exists" % id)
            return d
        d = model.Distribution(id, description, relativepath, family=family, \
                               variant=variant, version=version, timestamp=timestamp, \
                               files=files, arch=arch, repoids=repoids)
        self.collection.insert(d, safe=True)
        return d

    @audit(params=["id"])
    def delete(self, id, keep_files=False):
        """
        Delete distribution object based on "_id" key
        """
        if self.referenced(id):
            raise DistributionHasReferences(id)
        if not keep_files:
            distribution = self.distribution(id)
            distribution_path = "%s/%s" % (util.top_distribution_location(), distribution['id'])
            if os.path.exists(distribution_path):
                log.debug("Delete distribution %s" % id)
                shutil.rmtree(distribution_path)
                util.delete_empty_directories(os.path.dirname(distribution_path))
        self.collection.remove({'id':id}, safe=True)

    def referenced(self, id):
        """
        Get whether a distribution is referenced.
        @param id: A distribution ID.
        @type id: str
        @return: True if referenced
        @rtype: bool
        """
        collection = model.Repo.get_collection()
        repo = collection.find_one({"distributionid":id}, fields=["id"])
        return (repo is not None)

    @audit()
    def update(self, id, delta):
        """
        Updates a consumer object.
        @param id: The repo ID.
        @type id: str
        @param delta: A dict containing update keywords.
        @type delta: dict
        @return: The updated object
        @rtype: dict
        """
        delta.pop('id', None)
        dist = self.distribution(id)
        if not dist:
            raise PulpException('Distributon [%s] does not exist', id)
        for key, value in delta.items():
            # simple changes
            if key in ('description', 'relativepath', 'files', 'family', 'variant', 'version', 'arch'):
                dist[key] = value
                continue
            # unsupported
            raise Exception, \
                'update keyword "%s", not-supported' % key
        self.collection.save(dist, safe=True)

    def distribution(self, id):
        """
        Return a distribution object based on the id
        """
        distro = self.collection.find_one({'id': id})
        if distro:
            self.__make_ks_url(distro)
        return distro

    def distributions(self, spec={}):
        """
         Return all available distributions
        """
        distributions = list(self.collection.find(spec=spec))
        if not len(distributions):
            return []
        for distro in distributions:
            self.__make_ks_url(distro)
        return distributions

    def __make_ks_url(self, distribution):
        """
        construct a kickstart url for distribution
        """
        distribution['url'] = []
        server_name = config.config.get("server", "server_name")
        ks_url = config.config.get("server", "ks_url")
        collection = model.Repo.get_collection()
        repos = collection.find({"distributionid":distribution['id']}, fields=["id", "relative_path"])
        for repo in repos:
            url = "%s://%s%s/%s/" % ("http", server_name, ks_url, repo['relative_path'])
            distribution['url'].append(url)
        return distribution
