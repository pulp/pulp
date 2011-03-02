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

import re
import os
import pymongo
import logging
# Pulp
import pulp.server.util
from pulp.server.api.base import BaseApi
from pulp.server.auditing import audit
from pulp.server.db import model
from pymongo.errors import DuplicateKeyError
from pulp.server.pexceptions import PulpException

log = logging.getLogger(__name__)

filter_fields = model.Filter(None, None, None, None).keys()


class FilterApi(BaseApi):
      
    def _getcollection(self):
        return model.Filter.get_collection()

    @audit()
    def create(self, id, type, description=None, package_list=[]):
        """
        Create a new Filter object and return it
        """
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

    @audit()
    def clean(self):
        """
        Delete all the Filter objects in the database.  
        WARNING: Destructive
        """
        found = self.filters(fields=["id"])
        for f in found:
            self.delete(f["id"])

