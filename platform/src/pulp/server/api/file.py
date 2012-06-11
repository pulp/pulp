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
import os
import re

from pymongo.errors import DuplicateKeyError

# Pulp
import pulp.server.util
from pulp.server.api.base import BaseApi
from pulp.server.auditing import audit
from pulp.server.event.dispatcher import event
from pulp.server.db import model
from pulp.server.exceptions import PulpException

log = logging.getLogger(__name__)

file_fields = model.File(None, None, None, None, None, None).keys()

class FileHasReferences(Exception):

    MSG = 'file [%s] has references, delete not permitted'

    def __init__(self, id):
        Exception.__init__(self, self.MSG % id)

class FileApi(BaseApi):

    def _getcollection(self):
        return model.File.get_collection()

    @audit()
    def create(self, filename, checksum_type, checksum, size, description=None, repo_defined=False):
        """
        Create a new File object and return it
        """
        try:
            f = model.File(filename, checksum_type, checksum, size, description, repo_defined=repo_defined)
            self.collection.insert(f, safe=True)
            return f
        except DuplicateKeyError:
            log.error("file with name [%s] and checksum [%s] already exists" % (filename, checksum))
            return self.files(filename=filename, checksum=checksum, checksum_type=checksum_type)[0]

    @audit()
    def update(self, id, delta):
        """
        Updates a file object.
        @param id: The repo ID.
        @type id: str
        @param delta: A dict containing update keywords.
        @type delta: dict
        @return: The updated object
        @rtype: dict
        """
        delta.pop('id', None)
        file = self.file(id)
        if not file:
            raise PulpException('File [%s] does not exist', id)
        for key, value in delta.items():
            # simple changes
            if key in ('description',):
                file[key] = value
                continue
            # unsupported
            raise Exception, \
                'update keyword "%s", not-supported' % key
        self.collection.save(file, safe=True)

    @audit()
    def delete(self, id, keep_files=False):
        """
        Delete file object based on "id" key
        """
        fileobj = self.file(id)
        if not fileobj:
            log.error("File id [%s] not found " % id)
            return
        if self.referenced(id):
            raise FileHasReferences(id)
        file_path = "%s/%s/%s/%s/%s" % (pulp.server.util.top_file_location(), fileobj['filename'][:3],
                                        fileobj['filename'], fileobj['checksum']['sha256'],
                                        fileobj['filename'])
        self.collection.remove({'_id':id})
        if not keep_files:
            log.info("file path to be remove %s" % file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
                pulp.server.util.delete_empty_directories(os.path.dirname(file_path))
                self.__filedeleted(id, file_path)

    def file(self, id):
        """
        Return a single File object based on the filename and checksum
        """
        return self.collection.find_one({'id': id})

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
            return list(self.collection.find(fields=fields))
        else:
            return list(self.collection.find(searchDict, fields=fields))

    def referenced(self, id):
        """
        check if a file is referenced.
        @param id: A file ID.
        @type id: str
        @return: True if referenced
        @rtype: bool
        """
        collection = model.Repo.get_collection()
        repo = collection.find_one({"files":id}, fields=["id"])
        return (repo is not None)

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
        return list(self.collection.find({"id":{"$in":orphans}}, fields))

    def get_file_checksums(self, filenames):
        '''
        Fetch the package checksuums
        @param data: ["file_name", ...]
        @return  {"file_name": [<checksums>],...} 
        '''
        result = {}
        for i in self.collection.find({"filename":{"$in": filenames}}, ["filename", "checksum"]):
            result.setdefault(i["filename"], []).append(i["checksum"]["sha256"])
        return result

    @event(subject='file.deleted')
    def __filedeleted(self, id, path):
        # called to raise the event
        pass
