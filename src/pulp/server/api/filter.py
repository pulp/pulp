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


class FilterApi():

    def __init__(self):
        self.objectdb.ensure_index([
            ('id', pymongo.DESCENDING)],
            unique=True, background=True)

    @audit()
    def create(self, id, type, description=None, package_list=[]):
        """
        Create a new Filter object and return it
        """
        filter = self.filter(id)
        if filter is not None:
            raise PulpException("A Filter with id %s already exists" % id)

        f = model.Filter(id, type, description, package_list)
        collection = model.Filter.get_collection()
        collection.insert(f, safe=True)
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

        collection = model.Filter.get_collection()
        collection.remove({'id' : id}, safe=True)

    def filters(self, spec=None, fields=None):
        """
        Return a list of Filters
        """
        collection = model.Filter.get_collection()
        return list(collection.find(spec=spec, fields=fields))

    def filter(self, id, fields=None):
        """
        Return a single Filter object
        """
        filters = self.filters({'id': id}, fields)
        if not filters:
            return None
        return filters[0]


    def file(self, id):
        """
        Return a single File object based on the filename and checksum
        """
        return self.objectdb.find_one({'id': id})

    def files(self, filename=None, checksum=None, checksum_type=None, regex=None,
              fields=["id", "filename", "checksum", "size"]):
        """
        Return all available File objects based on the filename
        """
        searchDict = {}
        if filename:
            if regex:
                searchDict['filename'] = {"$regex":re.compile(filename)}
            else:
                searchDict['filename'] = filename
        if checksum_type and checksum:
            if regex:
                searchDict['checksum.%s' % checksum_type] = \
                    {"$regex":re.compile(checksum)}
            else:
                searchDict['checksum.%s' % checksum_type] = checksum
        if (len(searchDict.keys()) == 0):
            return list(self.objectdb.find(fields=fields))
        else:
            return list(self.objectdb.find(searchDict, fields=fields))

    def orphaned_files(self, fields=["filename", "checksum"]):
        #TODO: Revist this when model changes so we don't need to import RepoApi
        from pulp.server.api.repo import RepoApi
        rapi = RepoApi()
        repo_fileids = set()
        repos = rapi.repositories(fields=["files"])
        for r in repos:
            repo_fileids.update(r["files"])
        fils = self.files(fields=["id"])
        fileids = set([x["id"] for x in fils])
        orphans = list(fileids.difference(repo_fileids))
        return list(self.objectdb.find({"id":{"$in":orphans}}, fields))
