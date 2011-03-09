# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Red Hat, Inc.
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

import logging

from pulp.server.api.base import BaseApi
from pulp.server.auditing import audit
from pulp.server.db import model
from pulp.server.pexceptions import PulpException


log = logging.getLogger(__name__)

distribution_fields = model.Distribution(None, None, None, []).keys()


class DistributionApi(BaseApi):

    def _getcollection(self):
        return model.Distribution.get_collection()

    @audit(params=["id"])
    def create(self, id, description, relativepath, files=[]):
        """
        Create a new Distribution object and return it
        """
        d = self.distribution(id)
        if d:
            log.info("Distribution with id %s already exists" % id)
            return d
        d = model.Distribution(id, description, relativepath, files)
        self.collection.insert(d, safe=True)
        return d

    @audit(params=["id"])
    def delete(self, id):
        """
        Delete distribution object based on "_id" key
        """
        self.collection.remove({'id':id}, safe=True)

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
            if key in ('description', 'relativepath', 'files',):
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
        return self.collection.find_one({'id': id})

    def distributions(self):
        """
         Return all available distributions
        """
        return list(self.collection.find())

