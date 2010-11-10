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

import logging
from pulp.server.db import model
from pulp.server.auditing import audit
from pulp.server.api.base import BaseApi
from pulp.server.db.connection import get_object_db
log = logging.getLogger(__name__)

distribution_fields = model.Distribution(None, None, None, []).keys()


class DistributionApi(BaseApi):

    def __init__(self):
        BaseApi.__init__(self)

    @property
    def _indexes(self):
        return ["id", "files", "relativepath"]

    def _getcollection(self):
        return get_object_db('distribution',
                             self._unique_indexes,
                             self._indexes)

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
        self.insert(d)
        return d

    @audit(params=["id"])
    def delete(self, id):
        """
        Delete distribution object based on "_id" key
        """
        super(DistributionApi, self).delete(id=id)

    @audit()
    def update(self, distribution):
        """
        Updates an distribution object in the database
        """
        return super(DistributionApi, self).update(distribution)

    def distribution(self, id):
        """
        Return a distribution object based on the id
        """
        return self.objectdb.find_one({'id': id})

    def search_by_repo(self, repoid):
        """
        lookup distributions associated to a repo id
        """
        pass

