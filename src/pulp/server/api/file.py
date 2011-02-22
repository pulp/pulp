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
#from pulp.server.db.connection import get_object_db

log = logging.getLogger(__name__)

file_fields = model.File(None, None, None, None, None, None).keys()


class FileApi(BaseApi):

    def __init__(self):
        BaseApi.__init__(self)
        self.objectdb.ensure_index([
            ('filename', pymongo.DESCENDING),
            ('checksum', pymongo.DESCENDING)],
            unique=True, background=True)
    @property
    def _indexes(self):
        return []

    def _getcollection(self):
        #return get_object_db('file', self._unique_indexes, self._indexes)
        return model.File.get_collection()

    @property
    def _unique_indexes(self):
        return []

    @audit()
    def create(self, filename, checksum_type, checksum, size, description=None, repo_defined=False):
        """
        Create a new File object and return it
        """
        f = model.File(filename, checksum_type, checksum, size, description, repo_defined=repo_defined)
        self.insert(f)
        return f

    @audit()
    def delete(self, id, keep_files=False):
        """
        Delete file object based on "id" key
        """
        fileobj = self.file(id)
        file_path = "%s/%s/%s" % (pulp.server.util.top_package_location(), 
                                      fileobj['checksum']['sha256'][:3],
                                      fileobj['filename'])
        BaseApi.delete(self, _id=id)
        if not keep_files:
            log.info("file path to be remove %s" % file_path)
            if os.path.exists(file_path):
                os.remove(file_path)

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
