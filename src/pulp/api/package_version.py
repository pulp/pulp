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

    def __init__(self):
        BaseApi.__init__(self)
    
    def _get_unique_indexes(self):
        return []

    def _get_indexes(self):
        return ["packageid"]

    def _getcollection(self):
        return self.db.packageversions

    def create(self, packageid, epoch, version, release, arch):
        """
        Create a new PackageVersion object and return it
        """
        pv = model.PackageVersion(packageid, epoch, version, release, arch)
        self.objectdb.insert(pv)
        return pv
        
    def packageversion(self, id, filter=None):
        """
        Return a single PackageVersion object
        """
        return self.objectdb.find_one({'id': id})

    def packageversions(self):
        """
        List all packages.  Can be quite large
        """
        return list(self.objectdb.find())
