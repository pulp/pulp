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

import pymongo

# Pulp
from pulp import model
from pulp.api.base import BaseApi

class PackageVersionApi(BaseApi):

    def __init__(self, config):
        BaseApi.__init__(self, config)
        self.objectdb.ensure_index([('name', pymongo.DESCENDING), 
            ('epoch', pymongo.DESCENDING), 
            ('version', pymongo.DESCENDING),
            ('release', pymongo.DESCENDING),
            ('arch', pymongo.DESCENDING), 
            ('filename', pymongo.DESCENDING),
            ('checksum', pymongo.DESCENDING)], 
            unique=True, background=True)

    def _get_unique_indexes(self):
        return []

    def _get_indexes(self):
        return ["name", "filename", "checksum", "epoch", "version", "release",
                "arch", "description"]

    def _getcollection(self):
        return self.db.packageversions

    def create(self, name, epoch, version, release, arch, description, 
            checksum_type, checksum, filename):
        """
        Create a new PackageVersion object and return it
        """
        pv = model.PackageVersion(name, epoch, version, release, arch, description,
                checksum_type, checksum, filename)
        self.objectdb.insert(pv)
        return pv

    def delete(self, object):
        """
        Delete package version object based on "_id" key
        """
        self.objectdb.remove({"_id":object["_id"]})

    def packageversion(self, name=None, epoch=None, version=None, release=None, arch=None, 
            filename=None, checksum_type=None, checksum=None):
        """
        Return a list of all package version objects matching search terms
        """
        searchDict = {}
        if name:
            searchDict['name'] = name
        if epoch:
            searchDict['epoch'] = epoch
        if version:
            searchDict['version'] = version
        if release:
            searchDict['release'] = release
        if arch:
            searchDict['arch'] = arch
        if filename:
            searchDict['filename'] = filename
        if checksum_type and checksum:
            searchDict['checksum.%s' % checksum_type] = checksum
        return self.objectdb.find(searchDict)

    def packageversions(self):
        """
        List all packages.  Can be quite large
        """
        return list(self.objectdb.find())

    def packageversion_by_ivera(self, package_id, version, epoch, release, arch):
        """
        Returns the package version identified by the given package and VERA.
        """
        return self.objectdb.find_one({'packageid' : package_id, 'version' : version,
                                       'epoch' : epoch, 'release' : release, 'arch' : arch,})
                                       
    def package_descriptions(self):
        '''
        List of all package names and descriptions (will not contain package
        version information).
        '''
        return list(self.objectdb.find({}, {'packageid' : True, 'description' : True,}))
                                       
