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
from pulp.server.api.base import BaseApi
from pulp.server.auditing import audit
from pulp.server.db import model
#from pulp.server.db.connection import get_object_db
from pulp.server.api.depsolver import DepSolver
import pulp.server.util
from pulp.server.pexceptions import PulpException

log = logging.getLogger(__name__)

package_fields = model.Package(None, None, None, None, None, None, None, None, None).keys()


class PackageApi(BaseApi):

    def __init__(self):
        BaseApi.__init__(self)
        self.objectdb.ensure_index([('name', pymongo.DESCENDING),
            ('epoch', pymongo.DESCENDING),
            ('version', pymongo.DESCENDING),
            ('release', pymongo.DESCENDING),
            ('arch', pymongo.DESCENDING),
            ('filename', pymongo.DESCENDING),
            ('checksum', pymongo.DESCENDING)],
            unique=True, background=True)


    @property
    def _unique_indexes(self):
        return []

    @property
    def _indexes(self):
        return ["name", "filename", "checksum", "epoch", "version", "release",
                "arch", "description"]

    def _getcollection(self):
        #return get_object_db('packages', self._unique_indexes, self._indexes)
        return model.Package.get_collection()


    @audit()
    def create(self, name, epoch, version, release, arch, description,
            checksum_type, checksum, filename, repo_defined=False):
        """
        Create a new Package object and return it
        """
        p = model.Package(name, epoch, version, release, arch, description,
                checksum_type, checksum, filename, repo_defined=repo_defined)
        self.insert(p)
        return p

    @audit()
    def delete(self, id, keep_files=False):
        """
        Delete package version object based on "_id" key
        """
        if not keep_files:
            pkg = self.package(id)
            pkg_packages_path = pulp.server.util.get_shared_package_path(
                                           pkg["name"], pkg["version"], pkg["release"], pkg["arch"],
                                           pkg["filename"], pkg["checksum"])
            if os.path.exists(pkg_packages_path):
                log.debug("Delete package %s at %s" % (pkg["filename"], pkg_packages_path))
                os.remove(pkg_packages_path)
        BaseApi.delete(self, _id=id)

    def package(self, id):
        """
        Return a single Package object based on the id
        """
        return self.objectdb.find_one({'id': id})

    def packages(self, name=None, epoch=None, version=None, release=None, arch=None,
            filename=None, checksum_type=None, checksum=None, regex=False,
            fields=["id", "name", "epoch", "version", "release", "arch", "filename", "checksum"]):
        """
        Return a list of all package version objects matching search terms
        """
        searchDict = {}
        if name:
            if regex:
                searchDict['name'] = {"$regex":re.compile(name)}
            else:
                searchDict['name'] = name
        if epoch:
            if regex:
                searchDict['epoch'] = {"$regex":re.compile(epoch)}
            else:
                searchDict['epoch'] = epoch
        if version:
            if regex:
                searchDict['version'] = {"$regex":re.compile(version)}
            else:
                searchDict['version'] = version
        if release:
            if regex:
                searchDict['release'] = {"$regex":re.compile(release)}
            else:
                searchDict['release'] = release
        if arch:
            if regex:
                searchDict['arch'] = {"$regex":re.compile(arch)}
            else:
                searchDict['arch'] = arch
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

    def packages_by_id(self, pkg_ids, **kwargs):
        """
        @param pkg_ids list of package ids
        @type dictionary of package objects, key is package id
        @type kwargs: variable number of named keyword arguments
        @param kwargs: a variable number of arguments can be passed into 
                       the search query, example: name="pkg_name1", filename="file1.rpm"

        One use of this method is to query for a particular package inside of a repo. 
        First restrict the search to only ids in the repo, then refine to match the 
        desired query
        """
        search_dict = {"id":{"$in":pkg_ids}}
        for key in kwargs:
            search_dict[key] = kwargs[key]
        ret_data = {}
        tmp_data = self.objectdb.find(search_dict)
        for pkg in tmp_data:
            ret_data[pkg["id"]] = pkg
        return ret_data

    def package_filenames(self, spec=None):
        """
         Returns a list of all file names matching the spec
        """
        return list(self.objectdb.find(spec, fields=['filename', 'checksum']))

    def package_by_ivera(self, name, version, epoch, release, arch):
        """
        Returns the package version identified by the given package and VERA.
        """
        return self.objectdb.find_one({'name' : name, 'version' : version,
                                       'epoch' : epoch, 'release' : release, 'arch' : arch, })

    def package_descriptions(self, spec=None):
        '''
        List of all package names and descriptions (will not contain package
        version information).
        '''
        #return list(self.objectdb.find({}, {'name' : True, 'description' : True,}))
        return list(self.objectdb.find(spec, ['id', 'name', 'description']))

    def package_dependency(self, pkgnames=[], repoids=[], recursive=0):
        '''
         Get list of available dependencies for a given package in
         a specific repo
         @param repoid: The repo id
         @type repoid: str
         @param pkgnames: list of package names
         @type pkgnames: list
         @return list: nvera of dependencies
        '''
        from pulp.server.api.repo import RepoApi
        rapi = RepoApi()
        repos = []
        for rid in repoids:
            repoid = rapi.repository(rid)
            if not repoid:
                continue
            repos.append(repoid)
        dsolve = DepSolver(repos, pkgnames)
        if recursive:
            results = dsolve.getRecursiveDepList()
        else:
            results = dsolve.getDependencylist()
        deps = dsolve.processResults(results)
        pkgs = []
        log.info(" results from depsolver %s" % results)
        for dep in deps:
            name, version, epoch, release, arch = dep
            epkg = self.package_by_ivera(name, version, epoch, release, arch)
            if not epkg:
                continue
            pkgs.append(epkg)
        log.info("deps packages suggested %s" % deps)
        return {'dependency_list' : dsolve.printable_result(results),
                'available_packages' :pkgs}

    def package_checksum(self, filename):
        """
         Returns a list of checksum info for names matching the spec
        """
        spec = {'filename' : filename}
        return list(self.objectdb.find(spec, fields=['checksum']))

    def orphaned_packages(self, fields=["id", "filename", "checksum"]):
        #TODO: Revist this when model changes so we don't need to import RepoApi
        from pulp.server.api.repo import RepoApi
        rapi = RepoApi()
        repo_pkgids = set()
        repos = rapi.repositories(fields=["packages"])
        for r in repos:
            repo_pkgids.update(r["packages"])
        pkgs = self.packages(fields=["id"])
        pkgids = set([x["id"] for x in pkgs])
        orphans = list(pkgids.difference(repo_pkgids))
        return list(self.objectdb.find({"id":{"$in":orphans}}, fields))

    def get_package_checksums(self, filenames):
        '''
        Fetch the package checksuums
        @param data: ["file_name", ...]
        @return  {"file_name": [<checksums>],...} 
        '''
        result = {}
        for i in self.objectdb.find({"filename":{"$in": filenames}}, ["filename", "checksum"]):
            result.setdefault(i["filename"], []).append(i["checksum"]["sha256"])
        return result

