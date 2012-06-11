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
import re

# Pulp
from pulp.server import util
from pulp.server.api.base import BaseApi
from pulp.server.api.depsolver import DepSolver
from pulp.server.auditing import audit
from pulp.server.db import model
from pulp.server.event.dispatcher import event
from pulp.server.exceptions import PulpException


log = logging.getLogger(__name__)

package_fields = model.Package(None, None, None, None, None, None, None, None, None).keys()


class PackageHasReferences(Exception):

    MSG = 'package [%s] has references, delete not permitted'

    def __init__(self, id):
        Exception.__init__(self, self.MSG % id)


class PackageApi(BaseApi):

    def _getcollection(self):
        return model.Package.get_collection()

    @audit()
    def create(self, name, epoch, version, release, arch, description,
            checksum_type, checksum, filename, repo_defined=False, repoids=[]):
        """
        Create a new Package object and return it
        """
        p = model.Package(name, epoch, version, release, arch, description,
                checksum_type, checksum, filename, repo_defined=repo_defined, repoids=repoids)
        self.collection.insert(p, safe=True)
        return p

    @audit()
    def update(self, id, delta):
        """
        Updates a package object.
        @param id: The repo ID.
        @type id: str
        @param delta: A dict containing update keywords.
        @type delta: dict
        @return: The updated object
        @rtype: dict
        """
        delta.pop('id', None)
        pkg = self.package(id)
        if not pkg:
            raise PulpException('Package [%s] does not exist', id)
        for key, value in delta.items():
            # simple changes
            if key in ('description',
                       'requires',
                       'provides',
                       'download_url',
                       'buildhost',
                       'size',
                       'group',
                       'license',
                       'vendor',
                       'repoids',):
                pkg[key] = value
                continue
            raise Exception, \
                'update keyword "%s", not-supported' % key
        self.collection.save(pkg, safe=True)

    @audit()
    def delete(self, id, keep_files=False):
        """
        Delete package version object based on "_id" key
        """
        if self.referenced(id):
            raise PackageHasReferences(id)
        pkg = self.package(id)
        if pkg is None:
            return
        if not keep_files:
            pkg_packages_path = util.get_shared_package_path(
                                           pkg["name"], pkg["version"], pkg["release"], pkg["arch"],
                                           pkg["filename"], pkg["checksum"])
            if os.path.exists(pkg_packages_path):
                log.debug("Delete package %s at %s" % (pkg["filename"], pkg_packages_path))
                os.remove(pkg_packages_path)
                self.__pkgdeleted(id, pkg_packages_path)
                util.delete_empty_directories(os.path.dirname(pkg_packages_path))
        self.collection.remove({'_id':id})

    def package(self, id):
        """
        Return a single Package object based on the id
        """
        return self.collection.find_one({'id': id})

    def packages(self, name=None, epoch=None, version=None, release=None, arch=None,
            filename=None, checksum_type=None, checksum=None, regex=False,
            fields=["id", "name", "epoch", "version", "release", "arch", "filename", "checksum", "repoids"]):
        """
        Return a list of all package version objects matching search terms
        """
        searchDict = {}
        if name:
            if regex:
                searchDict['name'] = {
                    "$regex":util.compile_regular_expression(name)}
            else:
                searchDict['name'] = name
        if epoch:
            if regex:
                searchDict['epoch'] = {
                    "$regex":util.compile_regular_expression(epoch)}
            else:
                searchDict['epoch'] = epoch
        if version:
            if regex:
                searchDict['version'] = {
                    "$regex":util.compile_regular_expression(version)}
            else:
                searchDict['version'] = version
        if release:
            if regex:
                searchDict['release'] = {
                    "$regex":util.compile_regular_expression(release)}
            else:
                searchDict['release'] = release
        if arch:
            if regex:
                searchDict['arch'] = {
                    "$regex":util.compile_regular_expression(arch)}
            else:
                searchDict['arch'] = arch
        if filename:
            if regex:
                searchDict['filename'] = {
                    "$regex":util.compile_regular_expression(filename)}
            else:
                searchDict['filename'] = filename
        if checksum_type and checksum:
            if regex:
                searchDict['checksum.%s' % checksum_type] = \
                    {"$regex":util.compile_regular_expression(checksum)}
            else:
                searchDict['checksum.%s' % checksum_type] = checksum
        if (len(searchDict.keys()) == 0):
            return list(self.collection.find(fields=fields))
        else:
            return list(self.collection.find(searchDict, fields=fields))

    def referenced(self, id):
        """
        Get whether a package is referenced.
        @param id: A package ID.
        @type id: str
        @return: True if referenced
        @rtype: bool
        """
        collection = model.Repo.get_collection()
        repo = collection.find_one({"packages":id}, fields=["id"])
        return (repo is not None)


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
        tmp_data = self.collection.find(search_dict)
        for pkg in tmp_data:
            ret_data[pkg["id"]] = pkg
        return ret_data

    def package_filenames(self, spec=None):
        """
         Returns a list of all file names matching the spec
        """
        return list(self.collection.find(spec, fields=['filename', 'checksum']))

    def package_by_ivera(self, name, version, epoch, release, arch):
        """
        Returns the package version identified by the given package and VERA.
        """
        return self.collection.find_one({'name' : name, 'version' : version,
                                       'epoch' : epoch, 'release' : release, 'arch' : arch, })

    def package_descriptions(self, spec=None):
        '''
        List of all package names and descriptions (will not contain package
        version information).
        '''
        #return list(self.collection.find({}, {'name' : True, 'description' : True,}))
        return list(self.collection.find(spec, ['id', 'name', 'description']))

    def package_dependency(self, pkgnames=[], repoids=[], recursive=0, make_tree=0):
        '''
         Get list of available dependencies for a given package in
         a specific repo
         @param repoid: The repo id
         @type repoid: str
         @param pkgnames: list of package names
         @type pkgnames: list
         @return dict: dictionary of dependency info of the format {'printable_dependency_result' : '', 'resolved' : [], 'unresolved' : [], 'dependency_tree' : {}}
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
        solved, unsolved = dsolve.processResults(results)
        dep_pkgs_map = {}
        log.info(" results from depsolver %s" % results)
        for dep, pkgs in solved.items():
            dep_pkgs_map[dep] = []
            for pkg in pkgs:
                name, version, epoch, release, arch = pkg
                epkg = self.package_by_ivera(name, version, epoch, release, arch)
                if not epkg:
                    continue
                dep_pkgs_map[dep].append(epkg)
        log.debug("deps packages suggested %s" % solved)

        dep_result = {'printable_dependency_result' : dsolve.printable_result(results),
                      'resolved' :dep_pkgs_map,
                      'unresolved' : unsolved}
        if make_tree:
            dep_tree = {}
            dsolve.make_tree(pkgnames, results, dep_tree)
            dep_result['dependency_tree'] = dep_tree
        dsolve.cleanup()
        return dep_result


    def package_checksum(self, filename):
        """
         Returns a list of checksum info for names matching the spec
        """
        spec = {'filename' : filename}
        return list(self.collection.find(spec, fields=['checksum']))

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
        return list(self.collection.find({"id":{"$in":orphans}}, fields))

    def get_package_checksums(self, filenames):
        '''
        Fetch the package checksuums
        @param data: ["file_name", ...]
        @return  {filename: [<checksums>],...}
        '''
        result = {}
        for i in self.collection.find({"filename":{"$in": filenames}}, ["filename", "checksum"]):
            result.setdefault(i["filename"], []).append(i["checksum"]["sha256"])
        return result

    @event(subject='package.deleted')
    def __pkgdeleted(self, id, path):
        # called to raise the event
        pass

    def or_query(self, pkg_info, fields=None, restrict_ids=None):
        """
        Provides an 'or' query for multiple package queries
        @param pkg_info: list of queries[{"field":"value"},"field2":"value2"}]
        @param fields: optional, fields to return
        @param restrict_ids: optional, restrict the search to this list of possible package ids, used to restrict result to packages in a particular repo
        @return fields:  what fields to return
        """
        if not pkg_info:
            # cannot pass empty list to $or query
            return []
        q = {}
        q["$or"] = pkg_info
        if restrict_ids != None:
            # Note:  if restrict_ids is an empty list we want that to be passed in to the query
            # We only want to skip this check if restrict_ids is truly None
            q["id"] = {"$in":restrict_ids}
        return list(self.collection.find(q, fields))


