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
import pymongo
import logging
# Pulp
from pulp.server.api.base import BaseApi
from pulp.server.auditing import audit
from pulp.server.db import model
from pulp.server.db.connection import get_object_db
from pulp.server.api.depsolver import DepSolver

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
        return get_object_db('packages',
                             self._unique_indexes,
                             self._indexes)
        
        
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
    def delete(self, id):
        """
        Delete package version object based on "_id" key
        """
        BaseApi.delete(self, _id=id)
    
    def package(self, id):
        """
        Return a single Package object based on the id
        """
        return self.objectdb.find_one({'id': id})

    def packages(self, name=None, epoch=None, version=None, release=None, arch=None, 
            filename=None, checksum_type=None, checksum=None, regex=False,
            fields=["id", "name", "epoch", "version", "release", "arch", "filename"]):
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

    def package_filenames(self, spec=None):
        """
         Returns a list of all file names matching the spec
        """
        return list(self.objectdb.find(spec, fields=['filename']))

    def package_by_ivera(self, name, version, epoch, release, arch):
        """
        Returns the package version identified by the given package and VERA.
        """
        return self.objectdb.find_one({'name' : name, 'version' : version,
                                       'epoch' : epoch, 'release' : release, 'arch' : arch,})
                                       
    def package_descriptions(self, spec=None):
        '''
        List of all package names and descriptions (will not contain package
        version information).
        '''
        #return list(self.objectdb.find({}, {'name' : True, 'description' : True,}))
        return list(self.objectdb.find(spec, ['id', 'name', 'description']))
    
    def package_dependency(self, pkgnames=[], repoids=[]):
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
            repos.append(rapi.repository(rid))
        dsolve = DepSolver(repos, pkgnames)
        results =  dsolve.getDependencylist()
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

